"""Position evaluation coordinator integrating static heuristics, positional terms, and terminal states."""

from typing import Optional
import chess

from engine.config import EvaluationConfig
from engine.constants import MATE_SCORE
from engine.evaluation.center_control import evaluate_center_control
from engine.evaluation.coordination import evaluate_coordination
from engine.evaluation.game_phase import calculate_game_phase
from engine.evaluation.king_safety import evaluate_king_safety
from engine.evaluation.material import evaluate_material, get_material_breakdown
from engine.evaluation.mobility import evaluate_mobility
from engine.evaluation.pawn_structure import evaluate_pawn_structure
from engine.evaluation.piece_square import evaluate_piece_square
from engine.types import EvaluationBreakdown


def evaluate_position(
    board: chess.Board, config: Optional[EvaluationConfig] = None, ply: int = 0
) -> int:
    """
    Evaluates a position and returns an integer score in centipawns from White's perspective.
    
    Terminal overrides:
    - Checkmate: +(MATE_SCORE - ply) if Black is checkmated; -(MATE_SCORE - ply) if White is checkmated.
    - Draws: Stalemate, repetition, 50-move rule, or insufficient material evaluate strictly to 0 cp.
    - Non-terminal: Weighted combination of material balance, piece-square tables, mobility,
      pawn structure, center control, king safety, and piece coordination.
    
    Args:
        board: Authoritative board instance.
        config: Evaluation configuration with piece values, weights, and feature toggles.
        ply: Current search ply distance from root (used for mate distance weighting).
        
    Returns:
        Integer score in centipawns (+ favors White, - favors Black).
    """
    # 1. Checkmate takes precedence over all static heuristics
    if board.is_checkmate():
        return -(MATE_SCORE - ply) if board.turn == chess.WHITE else (MATE_SCORE - ply)

    # 2. Recognized draws strictly score zero
    if (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_seventyfive_moves()
        or board.is_fivefold_repetition()
        or board.is_repetition(3)
        or board.is_fifty_moves()
    ):
        return 0

    cfg = config or EvaluationConfig()
    phase = calculate_game_phase(board)

    # 3. Static material heuristic evaluation
    score = round(evaluate_material(board, cfg) * cfg.material_weight)

    # 4. Positional heuristics
    if cfg.use_pst and cfg.pst_weight > 0.0:
        score += round(evaluate_piece_square(board, phase, cfg) * cfg.pst_weight)

    if cfg.use_mobility and cfg.mobility_weight > 0.0:
        score += round(evaluate_mobility(board, cfg) * cfg.mobility_weight)

    if cfg.use_pawn_structure and cfg.pawn_structure_weight > 0.0:
        score += round(evaluate_pawn_structure(board, phase, cfg) * cfg.pawn_structure_weight)

    if cfg.use_center_control and cfg.center_control_weight > 0.0:
        score += round(evaluate_center_control(board, cfg) * cfg.center_control_weight)

    if cfg.use_king_safety and cfg.king_safety_weight > 0.0:
        score += round(evaluate_king_safety(board, phase, cfg) * cfg.king_safety_weight)

    if cfg.use_coordination and cfg.coordination_weight > 0.0:
        score += round(evaluate_coordination(board, cfg) * cfg.coordination_weight)

    return score


def evaluate_position_breakdown(
    board: chess.Board, config: Optional[EvaluationConfig] = None, ply: int = 0
) -> EvaluationBreakdown:
    """
    Returns static evaluation along with structural component breakdown.
    
    Guarantees that individual component scores sum exactly to total_cp.
    """
    if board.is_checkmate():
        score = -(MATE_SCORE - ply) if board.turn == chess.WHITE else (MATE_SCORE - ply)
        return EvaluationBreakdown(
            white_material=0,
            black_material=0,
            material_cp=0,
            total_cp=score,
            is_terminal=True,
            terminal_type="checkmate",
        )

    if (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_seventyfive_moves()
        or board.is_fivefold_repetition()
        or board.is_repetition(3)
        or board.is_fifty_moves()
    ):
        return EvaluationBreakdown(
            white_material=0,
            black_material=0,
            material_cp=0,
            total_cp=0,
            is_terminal=True,
            terminal_type="draw",
        )

    cfg = config or EvaluationConfig()
    phase = calculate_game_phase(board)

    mat_breakdown = get_material_breakdown(board, cfg)
    mat_score = round(mat_breakdown.material_cp * cfg.material_weight)

    pst_score = round(evaluate_piece_square(board, phase, cfg) * cfg.pst_weight) if (cfg.use_pst and cfg.pst_weight > 0.0) else 0
    mobility_score = round(evaluate_mobility(board, cfg) * cfg.mobility_weight) if (cfg.use_mobility and cfg.mobility_weight > 0.0) else 0
    pawn_score = round(evaluate_pawn_structure(board, phase, cfg) * cfg.pawn_structure_weight) if (cfg.use_pawn_structure and cfg.pawn_structure_weight > 0.0) else 0
    center_score = round(evaluate_center_control(board, cfg) * cfg.center_control_weight) if (cfg.use_center_control and cfg.center_control_weight > 0.0) else 0
    king_score = round(evaluate_king_safety(board, phase, cfg) * cfg.king_safety_weight) if (cfg.use_king_safety and cfg.king_safety_weight > 0.0) else 0
    coord_score = round(evaluate_coordination(board, cfg) * cfg.coordination_weight) if (cfg.use_coordination and cfg.coordination_weight > 0.0) else 0

    total_score = mat_score + pst_score + mobility_score + pawn_score + center_score + king_score + coord_score

    return EvaluationBreakdown(
        white_material=mat_breakdown.white_material,
        black_material=mat_breakdown.black_material,
        material_cp=mat_score,
        pst_cp=pst_score,
        mobility_cp=mobility_score,
        pawn_structure_cp=pawn_score,
        center_control_cp=center_score,
        king_safety_cp=king_score,
        coordination_cp=coord_score,
        game_phase=phase,
        total_cp=total_score,
        is_terminal=False,
        terminal_type=None,
    )
