"""King safety evaluation based on pawn shield, file openness, and king-zone attacks."""

from typing import Optional
import chess

from engine.config import EvaluationConfig

SHIELD_MISSING_SEMI_OPEN = 12
SHIELD_MISSING_OPEN = 20
SHIELD_ADVANCED_PENALTY = 6
KING_ZONE_ATTACK_WEIGHT = 4


def _evaluate_king_safety_for_color(
    board: chess.Board,
    color: chess.Color,
) -> int:
    """
    Evaluates defensive safety terms for a single King.
    
    Returns a non-positive integer score (0 = perfectly safe, negative = compromised).
    Uses 64-bit integer bitboards for maximum search throughput.
    """
    king_sq = board.king(color)
    if king_sq is None:
        return 0

    kf = chess.square_file(king_sq)
    enemy_color = not color

    penalty = 0

    # 1. King Zone attack pressure (3x3 grid around king)
    kz_mask = chess.BB_KING_ATTACKS[king_sq] | (1 << king_sq)
    for sq in chess.scan_forward(kz_mask):
        penalty += board.attackers_mask(enemy_color, sq).bit_count() * KING_ZONE_ATTACK_WEIGHT

    # 2. Pawn shield & file openness on files [kf - 1, kf, kf + 1]
    friendly_pawns = board.pieces_mask(chess.PAWN, color)
    enemy_pawns = board.pieces_mask(chess.PAWN, enemy_color)

    min_file = max(0, kf - 1)
    max_file = min(7, kf + 1)

    for file_idx in range(min_file, max_file + 1):
        file_mask = chess.BB_FILES[file_idx]
        f_pawns_on_file = friendly_pawns & file_mask

        if not f_pawns_on_file:
            if not (enemy_pawns & file_mask):
                penalty += SHIELD_MISSING_OPEN
            else:
                penalty += SHIELD_MISSING_SEMI_OPEN
        else:
            # Check for advanced shield pawns (loosened pawn shield)
            if color == chess.WHITE:
                for p_sq in chess.scan_forward(f_pawns_on_file):
                    r = chess.square_rank(p_sq)
                    if r > 1:
                        penalty += (r - 1) * SHIELD_ADVANCED_PENALTY
            else:
                for p_sq in chess.scan_forward(f_pawns_on_file):
                    r = chess.square_rank(p_sq)
                    if r < 6:
                        penalty += (6 - r) * SHIELD_ADVANCED_PENALTY

    return -penalty


def evaluate_king_safety(
    board: chess.Board,
    phase: float = 1.0,
    config: Optional[EvaluationConfig] = None,
) -> int:
    """
    Evaluates king safety in centipawns from White's perspective.
    
    Tapered by game phase so that king shelter is strictly prioritized in the opening and
    middlegame, while allowing king activity without penalty in the endgame.
    
    Args:
        board: Authoritative board position.
        phase: Game phase in [0.0, 1.0] (1.0 = middlegame, 0.0 = endgame).
        config: Evaluation configuration.
        
    Returns:
        Integer centipawns (White king safety minus Black king safety).
    """
    if phase <= 0.05:
        # King safety is not a liability in pure endgames; king activity is favored
        return 0

    white_safety = _evaluate_king_safety_for_color(board, chess.WHITE)
    black_safety = _evaluate_king_safety_for_color(board, chess.BLACK)

    # Taper safety penalty by game phase
    return round(phase * (white_safety - black_safety))
