"""Piece mobility evaluation based on safe pseudo-legal attack rays and absolute pin restrictions."""

from typing import Optional
import chess

from engine.config import EvaluationConfig

# Centipawn weights per safe destination square
MOBILITY_WEIGHTS = {
    chess.KNIGHT: 4,
    chess.BISHOP: 4,
    chess.ROOK: 3,
    chess.QUEEN: 2,
}


def _get_pawn_attacks_mask(pawns_bb: int, color: chess.Color) -> int:
    """Computes a 64-bit bitmask of all squares attacked by pawns of the given color."""
    if color == chess.WHITE:
        return ((pawns_bb & ~chess.BB_FILE_A) << 7) | ((pawns_bb & ~chess.BB_FILE_H) << 9)
    else:
        return ((pawns_bb & ~chess.BB_FILE_H) >> 7) | ((pawns_bb & ~chess.BB_FILE_A) >> 9)


def evaluate_mobility(
    board: chess.Board, config: Optional[EvaluationConfig] = None
) -> int:
    """
    Evaluates safe mobility for non-king, non-pawn pieces.
    
    Mobility Semantics:
    - Counts accessible squares from piece attack rays excluding friendly-occupied squares
      and squares directly defended by enemy pawns (safe destinations).
    - Filters moves by absolute pins: Pieces pinned to their own king have their mobility
      restricted strictly to the pin ray (via board.pin_mask); pinned knights have zero mobility.
    - Excludes King to prevent king exposure/wandering from being misclassified as active mobility.
    - Excludes Pawns as pawn advancement is evaluated independently in pawn structure.
    - Operates entirely on 64-bit integer bitmasks with zero object allocations.
    
    Args:
        board: Authoritative board position.
        config: Evaluation configuration.
        
    Returns:
        Integer centipawns (White mobility minus Black mobility).
    """
    w_occ = board.occupied_co[chess.WHITE]
    b_occ = board.occupied_co[chess.BLACK]

    w_pawns = board.pieces_mask(chess.PAWN, chess.WHITE)
    b_pawns = board.pieces_mask(chess.PAWN, chess.BLACK)

    w_pawn_attacks = _get_pawn_attacks_mask(w_pawns, chess.WHITE)
    b_pawn_attacks = _get_pawn_attacks_mask(b_pawns, chess.BLACK)

    white_score = 0
    black_score = 0

    for piece_type, weight in MOBILITY_WEIGHTS.items():
        # White pieces
        for sq in chess.scan_forward(board.pieces_mask(piece_type, chess.WHITE)):
            pin_mask = board.pin_mask(chess.WHITE, sq)
            safe_targets = board.attacks_mask(sq) & ~w_occ & ~b_pawn_attacks & pin_mask
            white_score += safe_targets.bit_count() * weight

        # Black pieces
        for sq in chess.scan_forward(board.pieces_mask(piece_type, chess.BLACK)):
            pin_mask = board.pin_mask(chess.BLACK, sq)
            safe_targets = board.attacks_mask(sq) & ~b_occ & ~w_pawn_attacks & pin_mask
            black_score += safe_targets.bit_count() * weight

    return white_score - black_score
