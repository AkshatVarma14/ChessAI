"""Piece coordination evaluation (bishop pair, open files, 7th rank, defended pieces)."""

from typing import Optional
import chess

from engine.config import EvaluationConfig

BISHOP_PAIR_BONUS = 30
ROOK_OPEN_FILE_BONUS = 20
ROOK_SEMI_OPEN_FILE_BONUS = 10
ROOK_ON_SEVENTH_BONUS = 20
DEFENDED_PIECE_BONUS = 3


def _evaluate_coordination_for_color(
    board: chess.Board,
    color: chess.Color,
) -> int:
    """
    Computes piece coordination bonuses for a single color.
    
    Uses 64-bit integer bitmasks with zero object allocations.
    """
    score = 0
    friendly_pawns = board.pieces_mask(chess.PAWN, color)
    enemy_pawns = board.pieces_mask(chess.PAWN, not color)

    # 1. Bishop pair bonus
    if board.pieces_mask(chess.BISHOP, color).bit_count() >= 2:
        score += BISHOP_PAIR_BONUS

    # 2. Rooks on open and semi-open files, and on the 7th rank
    rooks_mask = board.pieces_mask(chess.ROOK, color)
    for sq in chess.scan_forward(rooks_mask):
        rf = chess.square_file(sq)
        rr = chess.square_rank(sq)
        file_mask = chess.BB_FILES[rf]

        has_friendly_pawn = bool(friendly_pawns & file_mask)
        has_enemy_pawn = bool(enemy_pawns & file_mask)

        if not has_friendly_pawn and not has_enemy_pawn:
            score += ROOK_OPEN_FILE_BONUS
        elif not has_friendly_pawn and has_enemy_pawn:
            score += ROOK_SEMI_OPEN_FILE_BONUS

        # Rook on 7th rank (rank 7 for White, rank 2 for Black)
        if (color == chess.WHITE and rr == 6) or (color == chess.BLACK and rr == 1):
            score += ROOK_ON_SEVENTH_BONUS

    # 3. Defended pieces (minor and major pieces protected by friendly units)
    pieces_mask = (
        board.pieces_mask(chess.KNIGHT, color)
        | board.pieces_mask(chess.BISHOP, color)
        | board.pieces_mask(chess.ROOK, color)
        | board.pieces_mask(chess.QUEEN, color)
    )
    for sq in chess.scan_forward(pieces_mask):
        if board.attackers_mask(color, sq):
            score += DEFENDED_PIECE_BONUS

    return score


def evaluate_coordination(
    board: chess.Board, config: Optional[EvaluationConfig] = None
) -> int:
    """
    Evaluates piece coordination features in centipawns from White's perspective.
    
    Evaluates:
    - Bishop pair possession.
    - Rooks stationed on open or semi-open files.
    - Rooks active on the 7th rank.
    - Harmoniously defended pieces.
    
    Args:
        board: Authoritative board position.
        config: Evaluation configuration.
        
    Returns:
        Integer centipawns (White coordination minus Black coordination).
    """
    white_score = _evaluate_coordination_for_color(board, chess.WHITE)
    black_score = _evaluate_coordination_for_color(board, chess.BLACK)
    return white_score - black_score
