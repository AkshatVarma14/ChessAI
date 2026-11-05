"""Material point evaluation for chess positions."""

from typing import Optional
import chess

from engine.config import EvaluationConfig
from engine.types import EvaluationBreakdown


def evaluate_material(
    board: chess.Board, config: Optional[EvaluationConfig] = None
) -> int:
    """
    Computes static material balance in centipawns from White's perspective.
    
    Positive score indicates an advantage for White; negative indicates an advantage for Black.
    The king is not included as ordinary material.
    Uses native 64-bit bitboards with zero allocations.
    
    Args:
        board: The python-chess Board to evaluate.
        config: Configured piece values. Uses default EvaluationConfig if None.
        
    Returns:
        Integer centipawns (White material minus Black material).
    """
    cfg = config or EvaluationConfig()
    return (
        (board.pieces_mask(chess.PAWN, chess.WHITE).bit_count() - board.pieces_mask(chess.PAWN, chess.BLACK).bit_count()) * cfg.pawn_value
        + (board.pieces_mask(chess.KNIGHT, chess.WHITE).bit_count() - board.pieces_mask(chess.KNIGHT, chess.BLACK).bit_count()) * cfg.knight_value
        + (board.pieces_mask(chess.BISHOP, chess.WHITE).bit_count() - board.pieces_mask(chess.BISHOP, chess.BLACK).bit_count()) * cfg.bishop_value
        + (board.pieces_mask(chess.ROOK, chess.WHITE).bit_count() - board.pieces_mask(chess.ROOK, chess.BLACK).bit_count()) * cfg.rook_value
        + (board.pieces_mask(chess.QUEEN, chess.WHITE).bit_count() - board.pieces_mask(chess.QUEEN, chess.BLACK).bit_count()) * cfg.queen_value
    )


def get_material_breakdown(
    board: chess.Board, config: Optional[EvaluationConfig] = None
) -> EvaluationBreakdown:
    """
    Generates detailed material breakdown for diagnostic and UI analysis.
    
    Args:
        board: Board to inspect.
        config: Evaluation configuration.
        
    Returns:
        EvaluationBreakdown dataclass instance.
    """
    cfg = config or EvaluationConfig()
    w_p = board.pieces_mask(chess.PAWN, chess.WHITE).bit_count()
    w_n = board.pieces_mask(chess.KNIGHT, chess.WHITE).bit_count()
    w_b = board.pieces_mask(chess.BISHOP, chess.WHITE).bit_count()
    w_r = board.pieces_mask(chess.ROOK, chess.WHITE).bit_count()
    w_q = board.pieces_mask(chess.QUEEN, chess.WHITE).bit_count()

    b_p = board.pieces_mask(chess.PAWN, chess.BLACK).bit_count()
    b_n = board.pieces_mask(chess.KNIGHT, chess.BLACK).bit_count()
    b_b = board.pieces_mask(chess.BISHOP, chess.BLACK).bit_count()
    b_r = board.pieces_mask(chess.ROOK, chess.BLACK).bit_count()
    b_q = board.pieces_mask(chess.QUEEN, chess.BLACK).bit_count()

    white_material = (
        w_p * cfg.pawn_value
        + w_n * cfg.knight_value
        + w_b * cfg.bishop_value
        + w_r * cfg.rook_value
        + w_q * cfg.queen_value
    )
    black_material = (
        b_p * cfg.pawn_value
        + b_n * cfg.knight_value
        + b_b * cfg.bishop_value
        + b_r * cfg.rook_value
        + b_q * cfg.queen_value
    )

    net_material = white_material - black_material
    return EvaluationBreakdown(
        white_material=white_material,
        black_material=black_material,
        material_cp=net_material,
        total_cp=net_material,
        is_terminal=board.is_game_over(),
    )
