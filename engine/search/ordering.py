"""Move ordering, killer heuristics, history heuristics, and search context."""

import time
from typing import Dict, List, Optional, Tuple
import chess

from engine.config import EvaluationConfig


class SearchInterrupted(Exception):
    """Raised when search is interrupted by time or node limits."""

    def __init__(self, reason: str = "interrupted") -> None:
        super().__init__(f"Search interrupted: {reason}")
        self.reason = reason


class SearchContext:
    """
    Maintains search telemetry, budgets, limits, and dynamic heuristics.
    
    Shared across search plies and iterations to track:
    - Time and node limits with monotonic time tracking.
    - Killer move tables indexed by ply (stores up to 2 quiet moves per ply).
    - History heuristic tables indexed by (from_square, to_square).
    """

    def __init__(
        self,
        time_limit_ms: Optional[float] = None,
        max_nodes: Optional[int] = None,
        start_time: Optional[float] = None,
        transposition_table: Optional[object] = None,
    ) -> None:
        self.time_limit_ms = time_limit_ms
        self.max_nodes = max_nodes
        self.start_time = start_time if start_time is not None else time.perf_counter()
        self.transposition_table = transposition_table

        self.nodes_searched: int = 0
        self.quiescence_nodes: int = 0
        self.pruned_nodes: int = 0
        self.interrupted: bool = False
        self.interruption_reason: Optional[str] = None

        # Transposition table telemetry
        self.tt_probes: int = 0
        self.tt_hits: int = 0
        self.tt_cutoffs: int = 0
        self.tt_stores: int = 0

        # Killer heuristic: ply -> [killer1, killer2] (quiet moves only)
        self.killers: Dict[int, List[chess.Move]] = {}

        # History heuristic: (from_sq, to_sq) -> integer score
        self.history: Dict[Tuple[int, int], int] = {}

    def check_limits(self) -> None:
        """
        Verifies if search limits (node limit or time limit) have been exceeded.
        
        Raises:
            SearchInterrupted: When configured node or time limits are reached.
        """
        if self.max_nodes is not None and self.nodes_searched >= self.max_nodes:
            self.interrupted = True
            self.interruption_reason = "node_limit"
            raise SearchInterrupted("node_limit")

        if self.time_limit_ms is not None:
            elapsed_ms = (time.perf_counter() - self.start_time) * 1000
            if elapsed_ms >= self.time_limit_ms:
                self.interrupted = True
                self.interruption_reason = "time_limit"
                raise SearchInterrupted("time_limit")

    def increment_node(self) -> None:
        """Increments searched node count and checks against configured limits."""
        self.nodes_searched += 1
        self.check_limits()

    def increment_quiescence_node(self) -> None:
        """Increments quiescence and total searched node counts and checks against configured limits."""
        self.quiescence_nodes += 1
        self.nodes_searched += 1
        self.check_limits()

    def record_cutoff(self, move: chess.Move, ply: int, depth: int, board: chess.Board) -> None:
        """
        Updates killer and history heuristics when a beta cutoff occurs.
        
        Only quiet moves (non-captures, non-promotions) are recorded to prevent
        tactical captures from polluting quiet move tables.
        """
        self.pruned_nodes += 1

        # Only quiet moves are recorded for killer and history heuristics
        if board.is_capture(move) or move.promotion is not None:
            return

        # 1. Update Killer Moves (up to 2 per ply)
        ply_killers = self.killers.setdefault(ply, [])
        if not ply_killers:
            ply_killers.append(move)
        elif ply_killers[0] != move:
            if len(ply_killers) == 1:
                ply_killers.insert(0, move)
            else:
                ply_killers[1] = ply_killers[0]
                ply_killers[0] = move

        # 2. Update History Heuristic (depth squared reward)
        key = (move.from_square, move.to_square)
        bonus = depth * depth
        new_score = self.history.get(key, 0) + bonus
        self.history[key] = new_score

        # History aging / normalization if score exceeds threshold
        if new_score > 10_000:
            for k in list(self.history.keys()):
                self.history[k] //= 2


def score_move(
    move: chess.Move,
    board: chess.Board,
    ply: int,
    context: Optional[SearchContext] = None,
    eval_config: Optional[EvaluationConfig] = None,
    pv_move: Optional[chess.Move] = None,
    tt_move: Optional[chess.Move] = None,
) -> int:
    """
    Computes a sorting priority score for a legal move.
    
    Priority hierarchy:
    1. Transposition table move (2,000,000)
    2. PV move from previous iteration (1,000,000)
    3. Pawn promotions (200,000 - 250,000)
    4. Favorable captures via MVV-LVA (100,000 - 110,000)
    5. Equal / unfavorable captures via MVV-LVA (50,000 - 60,000)
    6. Killer moves (19,000 - 20,000)
    7. History heuristic quiet moves (1,000 - 11,000)
    8. Remaining quiet moves (0)
    """
    # 1. Transposition table move (highest priority)
    if tt_move is not None and move == tt_move:
        return 2_000_000

    cfg = eval_config or EvaluationConfig()

    # 2. PV move from iterative deepening
    if pv_move is not None and move == pv_move:
        return 1_000_000

    # 2. Pawn promotions
    if move.promotion is not None:
        match move.promotion:
            case chess.QUEEN:
                promo_val = 50_000
            case chess.KNIGHT:
                promo_val = 20_000
            case chess.ROOK:
                promo_val = 15_000
            case chess.BISHOP:
                promo_val = 10_000
            case _:
                promo_val = 5_000
        is_cap = 5_000 if board.is_capture(move) else 0
        return 200_000 + promo_val + is_cap

    # 3 & 4. Captures (MVV-LVA)
    if board.is_capture(move):
        # Determine victim centipawn value
        if board.is_en_passant(move):
            victim_val = cfg.pawn_value
        else:
            victim_piece = board.piece_at(move.to_square)
            victim_val = cfg.get_piece_value(victim_piece.piece_type) if victim_piece else cfg.pawn_value

        # Determine attacker centipawn value
        attacker_piece = board.piece_at(move.from_square)
        if attacker_piece is not None:
            if attacker_piece.piece_type == chess.KING:
                # King as attacker in MVV-LVA is treated as high-value (last resort attacker)
                attacker_val = 20_000
            else:
                attacker_val = cfg.get_piece_value(attacker_piece.piece_type)
        else:
            attacker_val = 0

        mvv_lva = victim_val * 10 - attacker_val

        # Favorable or equal exchange
        if victim_val >= attacker_val:
            return 100_000 + mvv_lva
        else:
            return 50_000 + mvv_lva

    # 5. Killer moves (quiet cutoffs)
    if context and ply in context.killers:
        killers = context.killers[ply]
        if len(killers) > 0 and move == killers[0]:
            return 20_000
        if len(killers) > 1 and move == killers[1]:
            return 19_000

    # 6. History heuristic (quiet moves)
    if context:
        hist_score = context.history.get((move.from_square, move.to_square), 0)
        if hist_score > 0:
            return 1_000 + min(hist_score, 10_000)

    # 7. Remaining quiet moves
    return 0


def order_moves(
    board: chess.Board,
    legal_moves: List[chess.Move],
    ply: int = 0,
    context: Optional[SearchContext] = None,
    eval_config: Optional[EvaluationConfig] = None,
    pv_move: Optional[chess.Move] = None,
    tt_move: Optional[chess.Move] = None,
) -> List[chess.Move]:
    """
    Orders legal moves by tactical and heuristic priority to maximize Alpha-Beta cutoffs.
    
    Guarantees:
    - Retains exactly the same set of legal moves (zero moves lost or invented).
    - Preserves stability of unrated quiet moves.
    - Never mutates the board.
    
    Args:
        board: Authoritative board position.
        legal_moves: List of valid legal moves.
        ply: Current search ply distance.
        context: SearchContext holding killer and history tables.
        eval_config: Piece values for MVV-LVA calculation.
        pv_move: Principal variation or best move from previous iteration.
        tt_move: Best move suggested by transposition table.
        
    Returns:
        Sorted list of moves ordered highest-priority first.
    """
    if len(legal_moves) <= 1:
        return legal_moves

    return sorted(
        legal_moves,
        key=lambda m: score_move(m, board, ply, context, eval_config, pv_move, tt_move),
        reverse=True,
    )
