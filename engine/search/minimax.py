"""Classical depth-limited Minimax adversarial search."""

import time
from typing import Optional
import chess

from engine.config import EvaluationConfig
from engine.constants import INFINITY, MATE_SCORE
from engine.evaluation.evaluator import evaluate_position
from engine.types import SearchResult


def _minimax(
    board: chess.Board,
    depth: int,
    ply: int,
    config: EvaluationConfig,
    stats: dict,
) -> int:
    """
    Recursive depth-limited Minimax tree evaluation.
    
    White maximizes the White-relative centipawn evaluation;
    Black minimizes the White-relative centipawn evaluation.
    """
    stats["nodes"] += 1

    # 1. Terminal condition checks (checkmate, stalemate, repetition, 50-move, insufficient)
    if (
        board.is_checkmate()
        or board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_seventyfive_moves()
        or board.is_fivefold_repetition()
        or board.is_repetition(3)
        or board.is_fifty_moves()
    ):
        return evaluate_position(board, config, ply)

    # 2. Maximum search depth reached
    if depth == 0:
        return evaluate_position(board, config, ply)

    # 3. Recursive legal branch exploration
    if board.turn == chess.WHITE:
        max_eval = -INFINITY
        for move in board.legal_moves:
            board.push(move)
            try:
                score = _minimax(board, depth - 1, ply + 1, config, stats)
                if score > max_eval:
                    max_eval = score
            finally:
                board.pop()
        return max_eval
    else:
        min_eval = INFINITY
        for move in board.legal_moves:
            board.push(move)
            try:
                score = _minimax(board, depth - 1, ply + 1, config, stats)
                if score < min_eval:
                    min_eval = score
            finally:
                board.pop()
        return min_eval


def minimax_search(
    board: chess.Board,
    depth: int,
    config: Optional[EvaluationConfig] = None,
    allocated_time_ms: Optional[float] = None,
    difficulty: Optional[str] = None,
) -> SearchResult:
    """
    Executes depth-limited Minimax search to determine the best legal move.
    
    Guarantees that the supplied board is never mutated upon completion or exception.
    
    Args:
        board: Position to search.
        depth: Search depth limit (>= 1).
        config: Evaluation configuration. Uses defaults if None.
        
    Returns:
        SearchResult containing the optimal legal move and execution telemetry.
    """
    if depth < 1:
        raise ValueError(f"Search depth must be >= 1, got {depth}")

    cfg = config or EvaluationConfig()
    stats = {"nodes": 0}
    start_time = time.perf_counter()

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        # Terminal state at root (no legal moves exist)
        score = evaluate_position(board, cfg, ply=0)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return SearchResult(
            best_move=None,
            best_move_uci=None,
            best_move_san=None,
            score_cp=score,
            depth=depth,
            nodes_searched=1,
            pruned_nodes=0,
            elapsed_ms=elapsed_ms,
            nodes_per_second=0,
            algorithm="minimax",
            is_checkmate=board.is_checkmate(),
            is_draw=not board.is_checkmate(),
            allocated_time_ms=allocated_time_ms,
            difficulty=difficulty,
        )

    best_move: Optional[chess.Move] = None
    is_white = board.turn == chess.WHITE

    if is_white:
        best_score = -INFINITY
        for move in legal_moves:
            board.push(move)
            try:
                score = _minimax(board, depth - 1, ply=1, config=cfg, stats=stats)
                if score > best_score or best_move is None:
                    best_score = score
                    best_move = move
            finally:
                board.pop()
    else:
        best_score = INFINITY
        for move in legal_moves:
            board.push(move)
            try:
                score = _minimax(board, depth - 1, ply=1, config=cfg, stats=stats)
                if score < best_score or best_move is None:
                    best_score = score
                    best_move = move
            finally:
                board.pop()

    elapsed_s = time.perf_counter() - start_time
    elapsed_ms = elapsed_s * 1000
    nps = int(stats["nodes"] / elapsed_s) if elapsed_s > 0 else 0

    best_uci = best_move.uci() if best_move else None
    best_san = board.san(best_move) if best_move else None
    is_mate = abs(best_score) >= (MATE_SCORE - 100)

    return SearchResult(
        best_move=best_move,
        best_move_uci=best_uci,
        best_move_san=best_san,
        score_cp=best_score,
        depth=depth,
        nodes_searched=stats["nodes"],
        pruned_nodes=0,  # Unpruned Minimax does not prune branches
        elapsed_ms=elapsed_ms,
        nodes_per_second=nps,
        algorithm="minimax",
        is_checkmate=is_mate,
        is_draw=best_score == 0 and board.is_game_over(),
        allocated_time_ms=allocated_time_ms,
        difficulty=difficulty,
    )
