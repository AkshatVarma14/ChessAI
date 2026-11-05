"""Custom Chess Engine Package.

Provides classical adversarial search (Minimax, Alpha-Beta pruning, Iterative Deepening)
and modular positional evaluation without neural networks or external engine dependencies.
"""

from typing import Optional, Union
import chess

from engine.config import EvaluationConfig, SearchConfig
from engine.difficulty import (
    DEFAULT_DIFFICULTY,
    DIFFICULTY_PROFILES,
    DifficultyLevel,
    DifficultyProfile,
    get_difficulty_profile,
    validate_difficulty,
)
from engine.evaluation.center_control import evaluate_center_control
from engine.evaluation.coordination import evaluate_coordination
from engine.evaluation.evaluator import evaluate_position, evaluate_position_breakdown
from engine.evaluation.game_phase import calculate_game_phase
from engine.evaluation.king_safety import evaluate_king_safety
from engine.evaluation.material import evaluate_material, get_material_breakdown
from engine.evaluation.mobility import evaluate_mobility
from engine.evaluation.pawn_structure import evaluate_pawn_structure
from engine.evaluation.piece_square import evaluate_piece_square
from engine.search.alpha_beta import alpha_beta_search
from engine.search.iterative_deepening import iterative_deepening_search
from engine.search.minimax import minimax_search
from engine.search.ordering import SearchContext, SearchInterrupted, order_moves
from engine.search.quiescence import quiescence_search
from engine.search.time_manager import DEFAULT_SAFETY_MARGIN_MS, TimeManager
from engine.search.transposition_table import Bound, TTEntry, TranspositionTable
from engine.search.zobrist import compute_zobrist_hash, update_zobrist_hash, verify_zobrist_hash
from engine.types import EvaluationBreakdown, SearchResult

__all__ = [
    "choose_move",
    "evaluate_position",
    "evaluate_position_breakdown",
    "evaluate_material",
    "get_material_breakdown",
    "evaluate_piece_square",
    "evaluate_mobility",
    "evaluate_pawn_structure",
    "evaluate_center_control",
    "evaluate_king_safety",
    "evaluate_coordination",
    "calculate_game_phase",
    "SearchConfig",
    "EvaluationConfig",
    "SearchResult",
    "EvaluationBreakdown",
    "DifficultyLevel",
    "DifficultyProfile",
    "DIFFICULTY_PROFILES",
    "DEFAULT_DIFFICULTY",
    "get_difficulty_profile",
    "validate_difficulty",
    "TimeManager",
    "DEFAULT_SAFETY_MARGIN_MS",
    "minimax_search",
    "alpha_beta_search",
    "iterative_deepening_search",
    "quiescence_search",
    "order_moves",
    "SearchContext",
    "SearchInterrupted",
    "Bound",
    "TTEntry",
    "TranspositionTable",
    "compute_zobrist_hash",
    "update_zobrist_hash",
    "verify_zobrist_hash",
]


def choose_move(
    board: chess.Board,
    config: Optional[SearchConfig] = None,
    eval_config: Optional[EvaluationConfig] = None,
    difficulty: Optional[Union[str, DifficultyLevel]] = None,
) -> SearchResult:
    """
    Selects the optimal legal move for the active player using custom adversarial search.
    
    Guarantees:
    - Never mutates the input board.
    - Selects moves strictly from board.legal_moves.
    - Score is strictly White-relative (+ favors White, - favors Black).
    - Honors depth, node count, and monotonic time limits.
    - Supports dynamic time management across five difficulty presets.
    
    Args:
        board: Authoritative python-chess Board.
        config: Search configuration specifying depth, algorithm, limits, and ordering.
        eval_config: Evaluation configuration with piece valuations and positional weights.
        difficulty: Optional named difficulty preset ('beginner', 'easy', 'medium', 'hard', 'expert').
        
    Returns:
        SearchResult containing the chosen legal move, score, completed depth, and telemetry.
    """
    eval_cfg = eval_config or EvaluationConfig()
    time_manager = TimeManager()

    if difficulty is not None:
        profile = get_difficulty_profile(difficulty)
        diff_label = profile.level.value
        active_time_manager = time_manager
        if config is None:
            cfg = profile.search_config
            allocated_ms = time_manager.allocate_time(board, profile)
            search_time_limit_ms = time_manager.get_effective_search_limit(
                allocated_ms, profile.min_time_ms
            )
        else:
            cfg = config
            allocated_ms = cfg.time_limit_ms
            search_time_limit_ms = cfg.time_limit_ms
    else:
        diff_label = None
        active_time_manager = None
        cfg = config or SearchConfig()
        allocated_ms = cfg.time_limit_ms
        search_time_limit_ms = cfg.time_limit_ms

    if cfg.algorithm == "iterative_deepening" or cfg.use_iterative_deepening:
        return iterative_deepening_search(
            board=board,
            max_depth=cfg.depth,
            config=eval_cfg,
            time_limit_ms=search_time_limit_ms,
            max_nodes=cfg.max_nodes,
            use_move_ordering=cfg.use_move_ordering,
            use_quiescence=cfg.use_quiescence,
            max_quiescence_depth=cfg.max_quiescence_depth,
            max_check_depth=cfg.max_check_depth,
            use_transposition_table=cfg.use_transposition_table,
            transposition_table_size_mb=cfg.transposition_table_size_mb,
            allocated_time_ms=allocated_ms,
            difficulty=diff_label,
            time_manager=active_time_manager,
        )

    match cfg.algorithm:
        case "minimax":
            return minimax_search(
                board,
                depth=cfg.depth,
                config=eval_cfg,
                allocated_time_ms=allocated_ms,
                difficulty=diff_label,
            )
        case "alpha_beta":
            return alpha_beta_search(
                board=board,
                depth=cfg.depth,
                config=eval_cfg,
                use_move_ordering=cfg.use_move_ordering,
                time_limit_ms=search_time_limit_ms,
                max_nodes=cfg.max_nodes,
                use_quiescence=cfg.use_quiescence,
                max_quiescence_depth=cfg.max_quiescence_depth,
                max_check_depth=cfg.max_check_depth,
                use_transposition_table=cfg.use_transposition_table,
                transposition_table_size_mb=cfg.transposition_table_size_mb,
                allocated_time_ms=allocated_ms,
                difficulty=diff_label,
            )
        case _:
            raise ValueError(f"Unsupported search algorithm: '{cfg.algorithm}'")
