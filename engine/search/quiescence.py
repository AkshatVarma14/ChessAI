"""Quiescence search for tactical stability and horizon mitigation."""

from typing import List, Optional, Tuple, Union
import chess

from engine.config import EvaluationConfig
from engine.constants import INFINITY, MATE_SCORE, UNRESOLVED_CHECK_PENALTY
from engine.evaluation.evaluator import evaluate_position
from engine.search.ordering import SearchContext, order_moves


def quiescence_search(
    board: chess.Board,
    alpha: int,
    beta: int,
    ply: int,
    q_depth: int = 0,
    config: Optional[EvaluationConfig] = None,
    context: Optional[SearchContext] = None,
    max_quiescence_depth: int = 8,
    max_check_depth: int = 2,
    return_path_dep: bool = False,
) -> Union[int, Tuple[int, bool]]:
    """
    Extends adversarial search on tactically active positions (captures, promotions, check evasions).
    
    Guarantees:
    - Stand-pat evaluation is strictly used only when the side to move is NOT in check.
    - If the side to move is in check, stand-pat is strictly prohibited; all legal check evasions are examined.
    - Checkmate and terminal draw conditions strictly override heuristic evaluations.
    - If max_quiescence_depth is reached while quiet, static evaluation is returned.
    - If max_quiescence_depth is reached while in check, search extends up to max_check_depth additional
      plies to resolve the check via legal evasions, avoiding false quiet cutoffs.
    - If the hard emergency bound (max_quiescence_depth + max_check_depth) is exceeded while still in check,
      a penalized score (-UNRESOLVED_CHECK_PENALTY for White, +UNRESOLVED_CHECK_PENALTY for Black) is applied
      rather than treating the position as quiet.
    - All moves are safely restored via try...finally: board.pop().
    - Quiescence nodes are incremented and checked against configured global node and time budgets.
    - Accurately tracks and propagates path-dependence when return_path_dep=True so repetition
      and fifty-move draws encountered in quiescence never contaminate transposition table entries.
    - Returns White-relative centipawn integer score (+ favors White, - favors Black).
    
    Args:
        board: Authoritative python-chess Board.
        alpha: Lower score bound for maximizing player (White).
        beta: Upper score bound for minimizing player (Black).
        ply: Total ply distance from root (for mate distance scoring).
        q_depth: Plies searched within quiescence search.
        config: Evaluation configuration.
        context: SearchContext tracking node/time limits and quiescence nodes.
        max_quiescence_depth: Maximum plies to extend quiescence search for quiet positions.
        max_check_depth: Additional plies allowed to resolve check when at quiescence depth limit.
        return_path_dep: Whether to return a (score, is_path_dependent) tuple.
        
    Returns:
        Integer score in centipawns, or tuple (score, is_path_dependent) if return_path_dep=True.
    """
    if context is not None:
        context.increment_quiescence_node()

    # 1. Terminal condition checks (highest priority)
    if (
        board.is_checkmate()
        or board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_seventyfive_moves()
        or board.is_fivefold_repetition()
        or board.is_repetition(3)
        or board.is_fifty_moves()
    ):
        score = evaluate_position(board, config, ply)
        is_pd = board.is_repetition(2) or board.is_fifty_moves()
        return (score, is_pd) if return_path_dep else score

    cfg = config or EvaluationConfig()
    in_check = board.is_check()
    is_pd = False

    # 2. Quiet Branch: side to move is NOT in check
    if not in_check:
        # If quiet and at/beyond maximum quiescence depth, return static evaluation
        if q_depth >= max_quiescence_depth:
            static_eval = evaluate_position(board, cfg, ply)
            is_pd = board.is_repetition(2) or board.is_fifty_moves()
            return (static_eval, is_pd) if return_path_dep else static_eval

        # Stand-pat evaluation is valid because side to move is not in check
        stand_pat = evaluate_position(board, cfg, ply)
        is_pd = board.is_repetition(2) or board.is_fifty_moves()

        if board.turn == chess.WHITE:
            # White (maximizing): if stand_pat already exceeds beta, cutoff immediately
            if stand_pat >= beta:
                return (stand_pat, is_pd) if return_path_dep else stand_pat
            if stand_pat > alpha:
                alpha = stand_pat
            max_eval = stand_pat
        else:
            # Black (minimizing): if stand_pat is already below alpha, cutoff immediately
            if stand_pat <= alpha:
                return (stand_pat, is_pd) if return_path_dep else stand_pat
            if stand_pat < beta:
                beta = stand_pat
            min_eval = stand_pat

        # When quiet, generate only tactical moves (captures and pawn promotions)
        tactical_moves = [
            m for m in board.legal_moves if board.is_capture(m) or m.promotion is not None
        ]
        if not tactical_moves:
            # Position is quiet: no captures or promotions available
            return (stand_pat, is_pd) if return_path_dep else stand_pat

    # 3. Check Evasion Branch: side to move IS in check
    else:
        # Stand-pat is strictly prohibited when in check (passing is illegal)
        if board.turn == chess.WHITE:
            max_eval = -INFINITY
        else:
            min_eval = INFINITY

        # Check emergency ceiling to prevent unbounded checking cycles
        emergency_ceiling = max_quiescence_depth + max_check_depth
        if q_depth >= emergency_ceiling:
            # Hard emergency bound reached while still in check.
            # Never return ordinary static evaluation as if quiet; apply an unresolved check penalty.
            static_eval = evaluate_position(board, cfg, ply)
            is_pd = board.is_repetition(2) or board.is_fifty_moves()
            if board.turn == chess.WHITE:
                penalized = static_eval - UNRESOLVED_CHECK_PENALTY
            else:
                penalized = static_eval + UNRESOLVED_CHECK_PENALTY
            return (penalized, is_pd) if return_path_dep else penalized

        # Under check and within check extension budget: examine all legal check evasions
        tactical_moves = list(board.legal_moves)
        if not tactical_moves:
            # No legal check evasions -> checkmate
            mate_score = -(MATE_SCORE - ply) if board.turn == chess.WHITE else (MATE_SCORE - ply)
            return (mate_score, False) if return_path_dep else mate_score

    # 4. Tactical move ordering (promotions, MVV-LVA captures, evasions)
    ordered_moves = order_moves(
        board=board,
        legal_moves=tactical_moves,
        ply=ply,
        context=context,
        eval_config=cfg,
    )

    # 5. Search tactical branches
    best_is_pd = is_pd if not in_check else False
    cutoff_is_pd = False
    has_cutoff = False

    if board.turn == chess.WHITE:
        for move in ordered_moves:
            board.push(move)
            try:
                child_res = quiescence_search(
                    board=board,
                    alpha=alpha,
                    beta=beta,
                    ply=ply + 1,
                    q_depth=q_depth + 1,
                    config=cfg,
                    context=context,
                    max_quiescence_depth=max_quiescence_depth,
                    max_check_depth=max_check_depth,
                    return_path_dep=True,
                )
                child_score, child_pd = child_res
                if child_score > max_eval:
                    max_eval = child_score
                    best_is_pd = child_pd
                if child_score > alpha:
                    alpha = child_score
            finally:
                board.pop()

            if beta <= alpha:
                has_cutoff = True
                cutoff_is_pd = child_pd
                break

        node_pd = (board.is_repetition(2) or board.is_fifty_moves()) or (cutoff_is_pd if has_cutoff else best_is_pd)
        return (max_eval, node_pd) if return_path_dep else max_eval
    else:
        for move in ordered_moves:
            board.push(move)
            try:
                child_res = quiescence_search(
                    board=board,
                    alpha=alpha,
                    beta=beta,
                    ply=ply + 1,
                    q_depth=q_depth + 1,
                    config=cfg,
                    context=context,
                    max_quiescence_depth=max_quiescence_depth,
                    max_check_depth=max_check_depth,
                    return_path_dep=True,
                )
                child_score, child_pd = child_res
                if child_score < min_eval:
                    min_eval = child_score
                    best_is_pd = child_pd
                if child_score < beta:
                    beta = child_score
            finally:
                board.pop()

            if beta <= alpha:
                has_cutoff = True
                cutoff_is_pd = child_pd
                break

        node_pd = (board.is_repetition(2) or board.is_fifty_moves()) or (cutoff_is_pd if has_cutoff else best_is_pd)
        return (min_eval, node_pd) if return_path_dep else min_eval
