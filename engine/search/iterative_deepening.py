"""Iterative deepening adversarial search controller."""

import time
from typing import Optional
import chess

from engine.config import EvaluationConfig
from engine.constants import MATE_SCORE
from engine.evaluation.evaluator import evaluate_position
from engine.search.alpha_beta import alpha_beta_search
from engine.search.ordering import SearchContext, SearchInterrupted, order_moves
from engine.search.transposition_table import TranspositionTable
from engine.types import SearchResult


def iterative_deepening_search(
    board: chess.Board,
    max_depth: int = 3,
    config: Optional[EvaluationConfig] = None,
    time_limit_ms: Optional[float] = None,
    max_nodes: Optional[int] = None,
    use_move_ordering: bool = True,
    use_quiescence: bool = False,
    max_quiescence_depth: int = 8,
    max_check_depth: int = 2,
    use_transposition_table: bool = True,
    transposition_table_size_mb: int = 16,
    allocated_time_ms: Optional[float] = None,
    difficulty: Optional[str] = None,
    time_manager: Optional[object] = None,
) -> SearchResult:
    """
    Executes iterative deepening adversarial search up to max_depth.
    
    Searches depth 1, 2, 3, ... progressively:
    - Retains killer moves, history heuristic scores, and Transposition Table across iterations.
    - Orders root moves using the principal variation (PV) move from the previous depth and TT move.
    - Honors strict time limits and node limits.
    - If interrupted mid-iteration, safely unwinds the search tree, discards the partial
      iteration, and returns the best move and score from the last fully completed iteration.
    - If interrupted before depth 1 completes, returns a safe legal fallback move.
    
    Guarantees:
    - Board state is 100% restored upon completion or interruption.
    - Never returns an illegal move.
    - Never returns a score or best move from a partially evaluated root iteration.
    
    Args:
        board: Authoritative python-chess Board.
        max_depth: Target search depth (>= 1).
        config: Evaluation configuration with piece values.
        time_limit_ms: Time budget in milliseconds (monotonic clock).
        max_nodes: Maximum nodes budget.
        use_move_ordering: Whether to enable heuristic move ordering.
        use_quiescence: Whether to extend search on tactical lines at depth 0.
        max_quiescence_depth: Maximum depth to extend tactical quiescence search.
        max_check_depth: Additional plies allowed to resolve check at quiescence depth limit.
        use_transposition_table: Whether to use transposition table caching.
        transposition_table_size_mb: Memory budget for transposition table in megabytes.
        
    Returns:
        SearchResult containing the optimal legal move, completed depth, and telemetry.
    """
    if max_depth < 1:
        raise ValueError(f"max_depth must be >= 1, got {max_depth}")

    cfg = config or EvaluationConfig()
    start_time = time.perf_counter()
    alloc_time = allocated_time_ms if allocated_time_ms is not None else time_limit_ms

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        score = evaluate_position(board, cfg, ply=0)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return SearchResult(
            best_move=None,
            best_move_uci=None,
            best_move_san=None,
            score_cp=score,
            depth=0,
            completed_depth=0,
            nodes_searched=1,
            pruned_nodes=0,
            elapsed_ms=elapsed_ms,
            nodes_per_second=0,
            algorithm="iterative_deepening",
            quiescence_nodes=0,
            tt_probes=0,
            tt_hits=0,
            tt_cutoffs=0,
            tt_stores=0,
            is_checkmate=board.is_checkmate(),
            is_draw=not board.is_checkmate(),
            is_interrupted=False,
            interruption_reason=None,
            allocated_time_ms=alloc_time,
            difficulty=difficulty,
        )

    # Establish search context (persisting killers, history, and TT across iterations)
    context = SearchContext(
        time_limit_ms=time_limit_ms,
        max_nodes=max_nodes,
        start_time=start_time,
    )
    if use_transposition_table:
        tt = TranspositionTable(size_mb=transposition_table_size_mb)
        tt.new_search()
        context.transposition_table = tt

    # Determine safe fallback move (in case interrupted before depth 1 finishes)
    if use_move_ordering:
        ordered_fallback = order_moves(board, legal_moves, ply=0, context=context, eval_config=cfg)
        fallback_move = ordered_fallback[0]
    else:
        fallback_move = legal_moves[0]

    last_completed_result: Optional[SearchResult] = None
    last_completed_pv: Tuple[List[str], List[str]] = ([], [])
    pv_move: Optional[chess.Move] = None
    pv_stable_iterations: int = 0
    previous_score: Optional[int] = None

    for current_depth in range(1, max_depth + 1):
        try:
            # Check limits prior to launching the next depth iteration
            context.check_limits()

            iteration_result = alpha_beta_search(
                board=board,
                depth=current_depth,
                config=cfg,
                context=context,
                use_move_ordering=use_move_ordering,
                pv_move=pv_move,
                use_quiescence=use_quiescence,
                max_quiescence_depth=max_quiescence_depth,
                max_check_depth=max_check_depth,
                use_transposition_table=use_transposition_table,
                transposition_table_size_mb=transposition_table_size_mb,
            )

            # Iteration finished completely
            if pv_move == iteration_result.best_move:
                pv_stable_iterations += 1
            else:
                pv_stable_iterations = 1
            last_completed_result = iteration_result
            pv_move = iteration_result.best_move

            # Immediately extract and preserve verified PV for this completed iteration
            if context.transposition_table and iteration_result.best_move:
                iter_pv_uci, iter_pv_san = context.transposition_table.extract_pv(
                    board,
                    max_length=current_depth,
                    first_move=iteration_result.best_move,
                )
            else:
                iter_pv_uci = [iteration_result.best_move_uci] if iteration_result.best_move_uci else []
                iter_pv_san = [iteration_result.best_move_san] if iteration_result.best_move_san else []

            if not iter_pv_uci and iteration_result.best_move_uci and iteration_result.best_move_san:
                iter_pv_uci = [iteration_result.best_move_uci]
                iter_pv_san = [iteration_result.best_move_san]

            last_completed_pv = (iter_pv_uci, iter_pv_san)

            # If checkmate is found, we can terminate early as no better line exists
            if abs(iteration_result.score_cp) >= (MATE_SCORE - current_depth):
                break

            # Dynamic time management: check if next iteration would overshoot budget
            if time_manager is not None and alloc_time is not None:
                elapsed_so_far = (time.perf_counter() - start_time) * 1000
                score_diff = (
                    abs(iteration_result.score_cp - previous_score)
                    if previous_score is not None
                    else None
                )
                if getattr(time_manager, "should_terminate_early", lambda **kw: False)(
                    elapsed_ms=elapsed_so_far,
                    allocated_ms=alloc_time,
                    completed_depth=current_depth,
                    pv_stable_iterations=pv_stable_iterations,
                    score_diff_cp=score_diff,
                ):
                    break

            previous_score = iteration_result.score_cp

        except SearchInterrupted as exc:
            context.interrupted = True
            context.interruption_reason = exc.reason
            break

    elapsed_s = time.perf_counter() - start_time
    elapsed_ms = elapsed_s * 1000
    nps = int(context.nodes_searched / elapsed_s) if elapsed_s > 0 else 0

    if last_completed_result is not None:
        pv_uci, pv_san = last_completed_pv
        return SearchResult(
            best_move=last_completed_result.best_move,
            best_move_uci=last_completed_result.best_move_uci,
            best_move_san=last_completed_result.best_move_san,
            score_cp=last_completed_result.score_cp,
            depth=last_completed_result.depth,
            completed_depth=last_completed_result.completed_depth,
            nodes_searched=context.nodes_searched,
            pruned_nodes=context.pruned_nodes,
            elapsed_ms=elapsed_ms,
            nodes_per_second=nps,
            algorithm="iterative_deepening",
            quiescence_nodes=context.quiescence_nodes,
            tt_probes=context.tt_probes,
            tt_hits=context.tt_hits,
            tt_cutoffs=context.tt_cutoffs,
            tt_stores=context.tt_stores,
            is_checkmate=last_completed_result.is_checkmate,
            is_draw=last_completed_result.is_draw,
            is_interrupted=context.interrupted,
            interruption_reason=context.interruption_reason,
            allocated_time_ms=alloc_time,
            difficulty=difficulty,
            pv_uci=pv_uci,
            pv_san=pv_san,
        )
    else:
        # Interrupted before depth 1 could complete: return safe fallback move
        fb_uci = fallback_move.uci()
        fb_san = board.san(fallback_move)
        return SearchResult(
            best_move=fallback_move,
            best_move_uci=fb_uci,
            best_move_san=fb_san,
            score_cp=evaluate_position(board, cfg),
            depth=1,
            completed_depth=0,
            nodes_searched=context.nodes_searched,
            pruned_nodes=context.pruned_nodes,
            elapsed_ms=elapsed_ms,
            nodes_per_second=nps,
            algorithm="iterative_deepening",
            quiescence_nodes=context.quiescence_nodes,
            tt_probes=context.tt_probes,
            tt_hits=context.tt_hits,
            tt_cutoffs=context.tt_cutoffs,
            tt_stores=context.tt_stores,
            is_checkmate=False,
            is_draw=False,
            is_interrupted=True,
            interruption_reason=context.interruption_reason,
            allocated_time_ms=alloc_time,
            difficulty=difficulty,
            pv_uci=[fb_uci],
            pv_san=[fb_san],
        )
