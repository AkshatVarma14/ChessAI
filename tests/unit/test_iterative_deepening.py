"""Unit tests for iterative deepening adversarial search."""

import pytest
import chess

from engine.constants import MATE_SCORE
from engine.search.iterative_deepening import iterative_deepening_search
from engine.search.alpha_beta import alpha_beta_search


class TestIterativeDeepening:
    """Verify progressive depth search, interruption handling, and fallback behavior."""

    def test_completes_successive_depths(self) -> None:
        """Search completes depth 1, 2, and 3, reporting completed_depth == 3."""
        board = chess.Board()
        res = iterative_deepening_search(board, max_depth=3)

        assert res.completed_depth == 3
        assert res.depth == 3
        assert res.best_move is not None
        assert res.best_move in list(board.legal_moves)
        assert res.is_interrupted is False
        assert res.interruption_reason is None
        assert res.nodes_searched > 0

    def test_interrupted_iteration_does_not_overwrite_previous_completed_result(self) -> None:
        """
        When an iteration (e.g. depth 4) is interrupted by a node or time budget,
        the search must return the result from the last fully completed depth (e.g. depth 3).
        """
        fen = "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1"
        board = chess.Board(fen)

        # Baseline: run full depth 2
        d2_result = alpha_beta_search(board, depth=2)

        # Now run iterative deepening up to depth 4, but set a node limit that allows
        # depth 2 to finish but interrupts during depth 3 or 4
        # d2 took ~600 nodes, so cap at 1500 nodes
        id_result = iterative_deepening_search(board, max_depth=4, max_nodes=d2_result.nodes_searched + 20)

        assert id_result.is_interrupted is True
        assert id_result.interruption_reason == "node_limit"
        # The completed depth must be at least 1 and strictly less than max_depth
        assert id_result.completed_depth >= 1
        assert id_result.completed_depth < 4
        assert id_result.best_move in list(board.legal_moves)

    def test_interruption_before_depth_1_returns_legal_fallback(self) -> None:
        """
        If the search is aborted before depth 1 can complete, it must safely return
        a valid legal fallback move with completed_depth=0 and is_interrupted=True.
        """
        board = chess.Board()
        # With max_nodes=1, the search will be interrupted almost immediately on ply 1
        res = iterative_deepening_search(board, max_depth=3, max_nodes=1)

        assert res.is_interrupted is True
        assert res.interruption_reason == "node_limit"
        assert res.completed_depth == 0
        assert res.best_move is not None
        assert res.best_move in list(board.legal_moves)

    def test_time_limit_enforced(self) -> None:
        """Search must abort when time budget expires without hanging."""
        board = chess.Board()
        # Set a very small time limit on a deep search
        res = iterative_deepening_search(board, max_depth=8, time_limit_ms=30.0)

        assert res.is_interrupted is True
        assert res.interruption_reason == "time_limit"
        assert res.best_move is not None
        assert res.best_move in list(board.legal_moves)

    def test_forced_mate_early_termination(self) -> None:
        """Iterative deepening terminates early once an optimal mate-in-1 is verified."""
        # Scholar's mate: White plays Qh5xf7#
        fen = "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B5/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4"
        board = chess.Board(fen)

        res = iterative_deepening_search(board, max_depth=5)
        assert res.best_move == chess.Move.from_uci("h5f7")
        assert res.score_cp == MATE_SCORE - 1
        assert res.is_checkmate is True
        # Since mate was found on depth 1, search stopped without needing to search depth 5
        assert res.completed_depth >= 1

    def test_terminal_position_at_root(self) -> None:
        """Position where no legal moves exist returns cleanly without error."""
        # Fool's mate terminal position
        fen_mated = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
        board = chess.Board(fen_mated)
        assert board.is_checkmate()

        res = iterative_deepening_search(board, max_depth=3)
        assert res.best_move is None
        assert res.score_cp == -MATE_SCORE
        assert res.is_checkmate is True
        assert res.completed_depth == 0
