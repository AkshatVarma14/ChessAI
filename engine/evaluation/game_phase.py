"""Game phase calculation for tapered evaluation blending."""

import chess

# Total phase points in standard starting position:
# 4 Knights (4) + 4 Bishops (4) + 4 Rooks (8) + 2 Queens (8) = 24
TOTAL_PHASE_POINTS = 24

PHASE_WEIGHTS = {
    chess.KNIGHT: 1,
    chess.BISHOP: 1,
    chess.ROOK: 2,
    chess.QUEEN: 4,
}


def calculate_game_phase(board: chess.Board) -> float:
    """
    Computes a normalized game phase metric in the range [0.0, 1.0].
    
    - 1.0 represents a full opening / complex middlegame (all major and minor pieces present).
    - 0.0 represents a pure endgame (only kings and pawns remaining).
    
    The calculation is deterministic, symmetric between colors, and avoids discontinuities.
    Uses native 64-bit piece bitboards for zero-allocation performance.
    
    Args:
        board: Authoritative python-chess Board.
        
    Returns:
        Float in [0.0, 1.0] indicating the proportion of non-pawn material remaining.
    """
    knights = board.pieces_mask(chess.KNIGHT, chess.WHITE) | board.pieces_mask(chess.KNIGHT, chess.BLACK)
    bishops = board.pieces_mask(chess.BISHOP, chess.WHITE) | board.pieces_mask(chess.BISHOP, chess.BLACK)
    rooks = board.pieces_mask(chess.ROOK, chess.WHITE) | board.pieces_mask(chess.ROOK, chess.BLACK)
    queens = board.pieces_mask(chess.QUEEN, chess.WHITE) | board.pieces_mask(chess.QUEEN, chess.BLACK)

    current_points = (
        knights.bit_count() * PHASE_WEIGHTS[chess.KNIGHT]
        + bishops.bit_count() * PHASE_WEIGHTS[chess.BISHOP]
        + rooks.bit_count() * PHASE_WEIGHTS[chess.ROOK]
        + queens.bit_count() * PHASE_WEIGHTS[chess.QUEEN]
    )

    # In positions with multiple promoted queens, clamp to maximum points
    clamped_points = min(TOTAL_PHASE_POINTS, current_points)
    return clamped_points / float(TOTAL_PHASE_POINTS)
