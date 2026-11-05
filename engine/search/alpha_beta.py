"""Adversarial Alpha-Beta pruning search with move ordering, search limits, and Transposition Table."""

import time
from typing import Optional, Tuple
import chess

from engine.config import EvaluationConfig
from engine.constants import INFINITY, MATE_SCORE
from engine.evaluation.evaluator import evaluate_position
from engine.search.ordering import SearchContext, SearchInterrupted, order_moves
from engine.search.quiescence import quiescence_search
from engine.search.transposition_table import Bound, TranspositionTable
from engine.search.zobrist import compute_zobrist_hash
from engine.types import SearchResult


def _alpha_beta(
    board: chess.Board,
    depth: int,
    ply: int,
    alpha: int,
    beta: int,
    config: EvaluationConfig,
    context: SearchContext,
    use_move_ordering: bool = True,
    use_quiescence: bool = False,
    max_quiescence_depth: int = 8,
    max_check_depth: int = 2,
    tt: Optional[TranspositionTable] = None,
) -> Tuple[int, bool]:
    """
    Recursive Alpha-Beta search maintaining [alpha, beta] window bounds.
    
    White (maximizing player) raises alpha;
    Black (minimizing player) lowers beta.
    A beta cutoff occurs when beta <= alpha.

    Returns:
        Tuple of (score, is_path_dependent).
    """
    context.increment_node()

    # 1. Terminal condition checks (highest priority: checkmate and rules draws)
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
        return score, is_pd

    # 2. Transposition Table Probe
    key = 0
    tt_move: Optional[chess.Move] = None
    max_extension = (max_quiescence_depth + max_check_depth) if use_quiescence else 0
    if tt is not None:
        key = compute_zobrist_hash(board)
        tt_score, suggested_move, is_cutoff = tt.probe(
            key=key,
            depth=depth,
            alpha=alpha,
            beta=beta,
            ply=ply,
            halfmove_clock=board.halfmove_clock,
            max_extension=max_extension,
        )
        context.tt_probes += 1
        if tt_score is not None:
            context.tt_hits += 1
        if is_cutoff and tt_score is not None:
            context.tt_cutoffs += 1
            # Entries in the TT are guaranteed path-independent,
            # so a valid TT cutoff score is guaranteed path-independent.
            return tt_score, False

        if suggested_move is not None and board.is_legal(suggested_move):
            tt_move = suggested_move

    # 3. Maximum search depth reached -> enter quiescence search if enabled
    if depth == 0:
        if use_quiescence:
            score, q_is_pd = quiescence_search(
                board=board,
                alpha=alpha,
                beta=beta,
                ply=ply,
                q_depth=0,
                config=config,
                context=context,
                max_quiescence_depth=max_quiescence_depth,
                max_check_depth=max_check_depth,
                return_path_dep=True,
            )
            is_pd = q_is_pd or board.is_repetition(2) or board.is_fifty_moves()
            return score, is_pd
        else:
            score = evaluate_position(board, config, ply)
            is_pd = board.is_repetition(2) or board.is_fifty_moves()
            return score, is_pd

    # 4. Recursive legal branch exploration with pruning
    legal_moves = list(board.legal_moves)
    if use_move_ordering:
        moves_to_search = order_moves(
            board=board,
            legal_moves=legal_moves,
            ply=ply,
            context=context,
            eval_config=config,
            tt_move=tt_move,
        )
    else:
        moves_to_search = legal_moves

    original_alpha = alpha
    original_beta = beta
    best_move_found: Optional[chess.Move] = None
    best_move_is_path_dep = False
    cutoff_is_path_dep = False
    has_cutoff = False
    any_child_path_dep = False

    if board.turn == chess.WHITE:
        max_eval = -INFINITY
        for move in moves_to_search:
            board.push(move)
            try:
                score, child_pd = _alpha_beta(
                    board=board,
                    depth=depth - 1,
                    ply=ply + 1,
                    alpha=alpha,
                    beta=beta,
                    config=config,
                    context=context,
                    use_move_ordering=use_move_ordering,
                    use_quiescence=use_quiescence,
                    max_quiescence_depth=max_quiescence_depth,
                    max_check_depth=max_check_depth,
                    tt=tt,
                )
                if child_pd:
                    any_child_path_dep = True
                if score > max_eval:
                    max_eval = score
                    best_move_found = move
                    best_move_is_path_dep = child_pd
                if score > alpha:
                    alpha = score
            finally:
                board.pop()

            # Beta cutoff (Black will avoid this line)
            if beta <= alpha:
                context.record_cutoff(move=move, ply=ply, depth=depth, board=board)
                has_cutoff = True
                cutoff_is_path_dep = child_pd
                break

        # Path-dependence resolution for White
        if board.is_repetition(2) or board.is_fifty_moves():
            node_path_dep = True
        elif has_cutoff:
            node_path_dep = cutoff_is_path_dep
        else:
            if max_eval > original_alpha:
                node_path_dep = best_move_is_path_dep
            else:
                node_path_dep = any_child_path_dep

        # Transposition table storage (White)
        if tt is not None and not context.interrupted:
            if max_eval <= original_alpha:
                bound = Bound.UPPER
            elif max_eval >= beta:
                bound = Bound.LOWER
            else:
                bound = Bound.EXACT

            if not node_path_dep:
                tt.store(
                    key=key,
                    depth=depth,
                    score=max_eval,
                    bound=bound,
                    best_move=best_move_found,
                    ply=ply,
                    halfmove_clock=board.halfmove_clock,
                )
                context.tt_stores += 1
            elif best_move_found is not None:
                # Do not store path-dependent scores; preserve best move for ordering
                tt.store_move_only(key=key, best_move=best_move_found)

        return max_eval, node_path_dep
    else:
        min_eval = INFINITY
        for move in moves_to_search:
            board.push(move)
            try:
                score, child_pd = _alpha_beta(
                    board=board,
                    depth=depth - 1,
                    ply=ply + 1,
                    alpha=alpha,
                    beta=beta,
                    config=config,
                    context=context,
                    use_move_ordering=use_move_ordering,
                    use_quiescence=use_quiescence,
                    max_quiescence_depth=max_quiescence_depth,
                    max_check_depth=max_check_depth,
                    tt=tt,
                )
                if child_pd:
                    any_child_path_dep = True
                if score < min_eval:
                    min_eval = score
                    best_move_found = move
                    best_move_is_path_dep = child_pd
                if score < beta:
                    beta = score
            finally:
                board.pop()

            # Alpha cutoff (White will avoid this line)
            if beta <= alpha:
                context.record_cutoff(move=move, ply=ply, depth=depth, board=board)
                has_cutoff = True
                cutoff_is_path_dep = child_pd
                break

        # Path-dependence resolution for Black
        if board.is_repetition(2) or board.is_fifty_moves():
            node_path_dep = True
        elif has_cutoff:
            node_path_dep = cutoff_is_path_dep
        else:
            if min_eval < original_beta:
                node_path_dep = best_move_is_path_dep
            else:
                node_path_dep = any_child_path_dep

        # Transposition table storage (Black)
        if tt is not None and not context.interrupted:
            if min_eval >= original_beta:
                bound = Bound.LOWER
            elif min_eval <= alpha:
                bound = Bound.UPPER
            else:
                bound = Bound.EXACT

            if not node_path_dep:
                tt.store(
                    key=key,
                    depth=depth,
                    score=min_eval,
                    bound=bound,
                    best_move=best_move_found,
                    ply=ply,
                    halfmove_clock=board.halfmove_clock,
                )
                context.tt_stores += 1
            elif best_move_found is not None:
                # Do not store path-dependent scores; preserve best move for ordering
                tt.store_move_only(key=key, best_move=best_move_found)

        return min_eval, node_path_dep


def alpha_beta_search(
    board: chess.Board,
    depth: int,
    config: Optional[EvaluationConfig] = None,
    context: Optional[SearchContext] = None,
    use_move_ordering: bool = True,
    time_limit_ms: Optional[float] = None,
    max_nodes: Optional[int] = None,
    pv_move: Optional[chess.Move] = None,
    use_quiescence: bool = False,
    max_quiescence_depth: int = 8,
    max_check_depth: int = 2,
    use_transposition_table: bool = True,
    transposition_table_size_mb: int = 16,
    allocated_time_ms: Optional[float] = None,
    difficulty: Optional[str] = None,
) -> SearchResult:
    """
    Executes Alpha-Beta search to determine the optimal legal move.
    
    Guarantees:
    - Board state is never corrupted (always restored via try...finally).
    - When use_quiescence=False and TT is disabled, produces the exact same score
      as unpruned Minimax for identical depth and evaluation.
    - When use_quiescence=True, extends tactical captures and check evasions beyond nominal depth.
    - Integrates Transposition Table caching with Zobrist hashing and mate normalization.
    - Accurately records nodes searched, pruned branches, and TT telemetry.
    - Honors time and node limits when configured.
    
    Args:
        board: Position to search.
        depth: Search depth limit (>= 1).
        config: Evaluation configuration. Uses defaults if None.
        context: Optional SearchContext shared across iterations.
        use_move_ordering: Whether to order moves (promotions, MVV-LVA, killers, history).
        time_limit_ms: Maximum time allowed in milliseconds.
        max_nodes: Maximum nodes allowed.
        pv_move: Best move from previous iteration to search first.
        use_quiescence: Whether to extend search on tactical lines at depth 0.
        max_quiescence_depth: Maximum depth to extend tactical quiescence search.
        max_check_depth: Additional plies allowed to resolve check at quiescence depth limit.
        use_transposition_table: Whether to use transposition table caching.
        transposition_table_size_mb: Memory budget for transposition table in megabytes.
        
    Returns:
        SearchResult containing the chosen legal move, score, and telemetry.
    """
    if depth < 1:
        raise ValueError(f"Search depth must be >= 1, got {depth}")

    start_time = time.perf_counter()
    cfg = config or EvaluationConfig()

    # Reuse or initialize SearchContext
    if context is None:
        ctx = SearchContext(time_limit_ms=time_limit_ms, max_nodes=max_nodes, start_time=start_time)
    else:
        ctx = context

    # Initialize Transposition Table if enabled
    tt: Optional[TranspositionTable] = None
    if use_transposition_table:
        if getattr(ctx, "transposition_table", None) is not None:
            tt = ctx.transposition_table
        else:
            tt = TranspositionTable(size_mb=transposition_table_size_mb)
            ctx.transposition_table = tt

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        elapsed_s = time.perf_counter() - start_time
        elapsed_ms = elapsed_s * 1000
        score = evaluate_position(board, cfg)
        return SearchResult(
            best_move=None,
            best_move_uci=None,
            best_move_san=None,
            score_cp=score,
            depth=depth,
            completed_depth=depth,
            nodes_searched=ctx.nodes_searched,
            pruned_nodes=ctx.pruned_nodes,
            elapsed_ms=elapsed_ms,
            nodes_per_second=0,
            algorithm="alpha_beta",
            quiescence_nodes=0,
            tt_probes=ctx.tt_probes,
            tt_hits=ctx.tt_hits,
            tt_cutoffs=ctx.tt_cutoffs,
            tt_stores=ctx.tt_stores,
            is_checkmate=board.is_checkmate(),
            is_draw=not board.is_checkmate(),
            allocated_time_ms=allocated_time_ms,
            difficulty=difficulty,
        )

    # Root probe in Transposition Table
    root_key = 0
    tt_move: Optional[chess.Move] = None
    max_extension = (max_quiescence_depth + max_check_depth) if use_quiescence else 0
    if tt is not None:
        root_key = compute_zobrist_hash(board)
        tt_score, suggested_move, is_cutoff = tt.probe(
            key=root_key,
            depth=depth,
            alpha=-INFINITY,
            beta=INFINITY,
            ply=0,
            halfmove_clock=board.halfmove_clock,
            max_extension=max_extension,
        )
        ctx.tt_probes += 1
        if tt_score is not None:
            ctx.tt_hits += 1
        if suggested_move is not None and board.is_legal(suggested_move):
            tt_move = suggested_move

    # Determine move ordering at root (PV move, TT move, promotions, captures, etc.)
    preferred_pv = pv_move or tt_move
    if use_move_ordering:
        root_moves = order_moves(
            board=board,
            legal_moves=legal_moves,
            ply=0,
            context=ctx,
            eval_config=cfg,
            pv_move=preferred_pv,
            tt_move=tt_move,
        )
    else:
        root_moves = legal_moves

    best_move: Optional[chess.Move] = None
    root_path_dep: bool = False
    is_white = board.turn == chess.WHITE
    alpha = -INFINITY
    beta = INFINITY

    try:
        ctx.check_limits()

        if is_white:
            best_score = -INFINITY
            for move in root_moves:
                board.push(move)
                try:
                    score, child_pd = _alpha_beta(
                        board=board,
                        depth=depth - 1,
                        ply=1,
                        alpha=alpha,
                        beta=beta,
                        config=cfg,
                        context=ctx,
                        use_move_ordering=use_move_ordering,
                        use_quiescence=use_quiescence,
                        max_quiescence_depth=max_quiescence_depth,
                        max_check_depth=max_check_depth,
                        tt=tt,
                    )
                    if score > best_score or best_move is None:
                        best_score = score
                        best_move = move
                        root_path_dep = child_pd
                    if score > alpha:
                        alpha = score
                finally:
                    board.pop()

                if beta <= alpha:
                    ctx.record_cutoff(move=move, ply=0, depth=depth, board=board)
                    break
        else:
            best_score = INFINITY
            for move in root_moves:
                board.push(move)
                try:
                    score, child_pd = _alpha_beta(
                        board=board,
                        depth=depth - 1,
                        ply=1,
                        alpha=alpha,
                        beta=beta,
                        config=cfg,
                        context=ctx,
                        use_move_ordering=use_move_ordering,
                        use_quiescence=use_quiescence,
                        max_quiescence_depth=max_quiescence_depth,
                        max_check_depth=max_check_depth,
                        tt=tt,
                    )
                    if score < best_score or best_move is None:
                        best_score = score
                        best_move = move
                        root_path_dep = child_pd
                    if score < beta:
                        beta = score
                finally:
                    board.pop()

                if beta <= alpha:
                    ctx.record_cutoff(move=move, ply=0, depth=depth, board=board)
                    break

        # Store completed root result in Transposition Table
        if tt is not None and not ctx.interrupted and best_move is not None:
            if not (board.is_repetition(2) or board.is_fifty_moves() or root_path_dep):
                tt.store(
                    key=root_key,
                    depth=depth,
                    score=best_score,
                    bound=Bound.EXACT,
                    best_move=best_move,
                    ply=0,
                    halfmove_clock=board.halfmove_clock,
                )
                ctx.tt_stores += 1
            else:
                tt.store_move_only(key=root_key, best_move=best_move)

    except SearchInterrupted as exc:
        if context is not None:
            raise exc

        # Handle interruption for standalone alpha_beta_search
        elapsed_s = time.perf_counter() - start_time
        elapsed_ms = elapsed_s * 1000
        fallback = best_move or root_moves[0]
        return SearchResult(
            best_move=fallback,
            best_move_uci=fallback.uci(),
            best_move_san=board.san(fallback),
            score_cp=best_score if best_move is not None else evaluate_position(board, cfg),
            depth=depth,
            completed_depth=0 if best_move is None else depth - 1,
            nodes_searched=ctx.nodes_searched,
            pruned_nodes=ctx.pruned_nodes,
            elapsed_ms=elapsed_ms,
            nodes_per_second=int(ctx.nodes_searched / elapsed_s) if elapsed_s > 0 else 0,
            algorithm="alpha_beta",
            quiescence_nodes=ctx.quiescence_nodes,
            tt_probes=ctx.tt_probes,
            tt_hits=ctx.tt_hits,
            tt_cutoffs=ctx.tt_cutoffs,
            tt_stores=ctx.tt_stores,
            is_checkmate=False,
            is_draw=False,
            is_interrupted=True,
            interruption_reason=exc.reason,
            allocated_time_ms=allocated_time_ms,
            difficulty=difficulty,
        )

    elapsed_s = time.perf_counter() - start_time
    elapsed_ms = elapsed_s * 1000
    nps = int(ctx.nodes_searched / elapsed_s) if elapsed_s > 0 else 0

    best_uci = best_move.uci() if best_move else None
    best_san = board.san(best_move) if best_move else None
    is_mate = abs(best_score) >= (MATE_SCORE - 100)

    pv_uci: List[str] = []
    pv_san: List[str] = []
    if tt is not None and best_move is not None:
        pv_uci, pv_san = tt.extract_pv(board, max_length=depth, first_move=best_move)
    elif tt is not None:
        pv_uci, pv_san = tt.extract_pv(board, max_length=depth)
    if not pv_uci and best_move is not None and best_uci and best_san:
        pv_uci = [best_uci]
        pv_san = [best_san]

    return SearchResult(
        best_move=best_move,
        best_move_uci=best_uci,
        best_move_san=best_san,
        score_cp=best_score,
        depth=depth,
        completed_depth=depth,
        nodes_searched=ctx.nodes_searched,
        pruned_nodes=ctx.pruned_nodes,
        elapsed_ms=elapsed_ms,
        nodes_per_second=nps,
        algorithm="alpha_beta",
        quiescence_nodes=ctx.quiescence_nodes,
        tt_probes=ctx.tt_probes,
        tt_hits=ctx.tt_hits,
        tt_cutoffs=ctx.tt_cutoffs,
        tt_stores=ctx.tt_stores,
        is_checkmate=is_mate,
        is_draw=best_score == 0 and board.is_game_over(),
        is_interrupted=False,
        interruption_reason=None,
        allocated_time_ms=allocated_time_ms,
        difficulty=difficulty,
        pv_uci=pv_uci,
        pv_san=pv_san,
    )
