"""Center control and central square occupation evaluation."""

from typing import Optional
import chess

from engine.config import EvaluationConfig

SWEET_CENTER = (chess.D4, chess.E4, chess.D5, chess.E5)
EXTENDED_CENTER = (
    chess.C4, chess.F4, chess.C5, chess.F5,
    chess.D3, chess.E3, chess.D6, chess.E6,
)

SWEET_CENTER_BB = sum(1 << sq for sq in SWEET_CENTER)
EXTENDED_CENTER_BB = sum(1 << sq for sq in EXTENDED_CENTER)

OCCUPATION_BONUS_PAWN = 15
OCCUPATION_BONUS_MINOR = 10
CONTROL_BONUS_ATTACK = 5
EXTENDED_OCCUPATION_PAWN = 5


def evaluate_center_control(
    board: chess.Board, config: Optional[EvaluationConfig] = None
) -> int:
    """
    Evaluates occupation and control of central squares in centipawns from White's perspective.
    
    Evaluates:
    - Direct occupation of sweet center squares (d4, e4, d5, e5) by pawns and minor pieces.
    - Attack pressure / control exerted on sweet center squares by friendly vs enemy pieces.
    - Pawn presence in the extended center (c4, f4, c5, f5, d3, e3, d6, e6).
    
    Uses 64-bit integer bitmasks with zero object allocations.
    
    Args:
        board: Authoritative board position.
        config: Evaluation configuration.
        
    Returns:
        Integer centipawns (White central score minus Black central score).
    """
    white_score = 0
    black_score = 0

    w_pawns = board.pieces_mask(chess.PAWN, chess.WHITE)
    b_pawns = board.pieces_mask(chess.PAWN, chess.BLACK)
    w_minors = board.pieces_mask(chess.KNIGHT, chess.WHITE) | board.pieces_mask(chess.BISHOP, chess.WHITE)
    b_minors = board.pieces_mask(chess.KNIGHT, chess.BLACK) | board.pieces_mask(chess.BISHOP, chess.BLACK)

    # 1. Sweet center occupation
    white_score += (w_pawns & SWEET_CENTER_BB).bit_count() * OCCUPATION_BONUS_PAWN
    black_score += (b_pawns & SWEET_CENTER_BB).bit_count() * OCCUPATION_BONUS_PAWN
    white_score += (w_minors & SWEET_CENTER_BB).bit_count() * OCCUPATION_BONUS_MINOR
    black_score += (b_minors & SWEET_CENTER_BB).bit_count() * OCCUPATION_BONUS_MINOR

    # 2. Sweet center attack pressure
    for sq in SWEET_CENTER:
        white_score += board.attackers_mask(chess.WHITE, sq).bit_count() * CONTROL_BONUS_ATTACK
        black_score += board.attackers_mask(chess.BLACK, sq).bit_count() * CONTROL_BONUS_ATTACK

    # 3. Extended center pawn presence
    white_score += (w_pawns & EXTENDED_CENTER_BB).bit_count() * EXTENDED_OCCUPATION_PAWN
    black_score += (b_pawns & EXTENDED_CENTER_BB).bit_count() * EXTENDED_OCCUPATION_PAWN

    return white_score - black_score
