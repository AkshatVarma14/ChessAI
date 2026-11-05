"""Independent multi-feature pawn structure evaluation."""

from typing import Optional
import chess

from engine.config import EvaluationConfig

PASSED_PAWN_BONUS = {
    1: 10,   # White Rank 2 / Black Rank 7
    2: 15,   # White Rank 3 / Black Rank 6
    3: 25,   # White Rank 4 / Black Rank 5
    4: 45,   # White Rank 5 / Black Rank 4
    5: 75,   # White Rank 6 / Black Rank 3
    6: 120,  # White Rank 7 / Black Rank 2
}

ISOLATED_PAWN_PENALTY = 15
DOUBLED_PAWN_PENALTY = 15
CONNECTED_PAWN_BONUS = 10


# Precomputed 64-element bitboard tables for passed pawn detection
def _generate_passed_pawn_masks() -> dict[chess.Color, tuple[int, ...]]:
    masks: dict[chess.Color, list[int]] = {chess.WHITE: [0] * 64, chess.BLACK: [0] * 64}
    for sq in range(64):
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        adj_files = chess.BB_FILES[f]
        if f > 0:
            adj_files |= chess.BB_FILES[f - 1]
        if f < 7:
            adj_files |= chess.BB_FILES[f + 1]

        # White passed pawn: no enemy pawns ahead (ranks > r)
        w_ranks = 0
        for r_above in range(r + 1, 8):
            w_ranks |= chess.BB_RANKS[r_above]
        masks[chess.WHITE][sq] = adj_files & w_ranks

        # Black passed pawn: no enemy pawns ahead (ranks < r)
        b_ranks = 0
        for r_below in range(0, r):
            b_ranks |= chess.BB_RANKS[r_below]
        masks[chess.BLACK][sq] = adj_files & b_ranks

    return {
        chess.WHITE: tuple(masks[chess.WHITE]),
        chess.BLACK: tuple(masks[chess.BLACK]),
    }


PASSED_PAWN_MASKS = _generate_passed_pawn_masks()


def _evaluate_color_pawns(
    board: chess.Board,
    color: chess.Color,
    phase: float = 1.0,
) -> int:
    """
    Evaluates pawn structure features for a single color independently.
    
    In accordance with architectural standards, features are calculated independently
    without mutual-exclusion priority ladders (a pawn can be passed, isolated, and doubled).
    Uses 64-bit integer bitboards for maximum search throughput.
    """
    friendly_pawns = board.pieces_mask(chess.PAWN, color)
    enemy_pawns = board.pieces_mask(chess.PAWN, not color)
    passed_mask_table = PASSED_PAWN_MASKS[color]
    guard_mask_table = chess.BB_PAWN_ATTACKS[not color]

    # 1. Doubled pawns: Count pawns per file
    file_counts = [0] * 8
    for sq in chess.scan_forward(friendly_pawns):
        file_counts[chess.square_file(sq)] += 1

    doubled_penalty = 0
    for count in file_counts:
        if count > 1:
            doubled_penalty += (count - 1) * DOUBLED_PAWN_PENALTY

    score = -doubled_penalty
    endgame_multiplier = 1.0 + (1.0 - phase) * 0.5

    # Evaluate each friendly pawn for passed, isolated, and connected features
    for sq in chess.scan_forward(friendly_pawns):
        f = chess.square_file(sq)
        r = chess.square_rank(sq)

        # 2. Isolated pawn: No friendly pawns on adjacent files
        has_left_neighbor = (f > 0) and (file_counts[f - 1] > 0)
        has_right_neighbor = (f < 7) and (file_counts[f + 1] > 0)
        if not has_left_neighbor and not has_right_neighbor:
            score -= ISOLATED_PAWN_PENALTY

        # 3. Passed pawn: No enemy pawns ahead on the same or adjacent files
        if not (enemy_pawns & passed_mask_table[sq]):
            advancement = r if color == chess.WHITE else (7 - r)
            base_bonus = PASSED_PAWN_BONUS.get(advancement, 0)
            score += round(base_bonus * endgame_multiplier)

        # 4. Connected / Protected pawn: Guarded by friendly pawn diagonally behind
        if friendly_pawns & guard_mask_table[sq]:
            score += CONNECTED_PAWN_BONUS

    return score


def evaluate_pawn_structure(
    board: chess.Board,
    phase: float = 1.0,
    config: Optional[EvaluationConfig] = None,
) -> int:
    """
    Evaluates pawn structure features in centipawns from White's perspective.
    
    Args:
        board: Authoritative board position.
        phase: Game phase in [0.0, 1.0].
        config: Evaluation configuration.
        
    Returns:
        Integer centipawns (White pawn score minus Black pawn score).
    """
    white_score = _evaluate_color_pawns(board, chess.WHITE, phase)
    black_score = _evaluate_color_pawns(board, chess.BLACK, phase)
    return white_score - black_score
