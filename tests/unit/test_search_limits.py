"""Unit tests for search limits (time, nodes), interruption safety, and board immutability."""

import pytest
import chess

from engine import choose_move, SearchConfig
from engine.search.alpha_beta import alpha_beta_search
from engine.search.iterative_deepening import iterative_deepening_search
from engine.search.ordering import SearchContext, SearchInterrupted


class TestSearchLimitsAndInterruption:
    """Verify time/node budgets, cancellation unwinding, and board restoration."""

    def test_node_limit_enforced_in_alpha_beta(self) -> None:
        """Standalone Alpha-Beta search halts when node limit is reached."""
        board = chess.Board()
        res = alpha_beta_search(board, depth=5, max_nodes=50)

        assert res.is_interrupted is True
        assert res.interruption_reason == "node_limit"
        assert res.best_move is not None
        assert res.best_move in list(board.legal_moves)
        # Checked within small epsilon of the limit
        assert res.nodes_searched <= 60

    def test_time_limit_enforced_in_alpha_beta(self) -> None:
        """Standalone Alpha-Beta search halts when time limit expires."""
        board = chess.Board()
        res = alpha_beta_search(board, depth=8, time_limit_ms=25.0)

        assert res.is_interrupted is True
        assert res.interruption_reason == "time_limit"
        assert res.best_move is not None
        assert res.best_move in list(board.legal_moves)

    def test_board_state_unmutated_after_normal_completion(self) -> None:
        """Board FEN, turn, castling rights, and move stack must remain identical after search."""
        board = chess.Board()
        initial_fen = board.fen()

        choose_move(board, SearchConfig(depth=3, algorithm="alpha_beta"))
        assert board.fen() == initial_fen
        assert len(board.move_stack) == 0

        choose_move(board, SearchConfig(depth=3, algorithm="iterative_deepening"))
        assert board.fen() == initial_fen
        assert len(board.move_stack) == 0

    def test_board_state_unmutated_after_interrupted_search(self) -> None:
        """Board state must be 100% unwound and restored when an interruption occurs deep in the tree."""
        # Tactical position with deep branching
        fen = "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1"
        board = chess.Board(fen)
        initial_fen = board.fen()

        # Interrupted search via node limit
        res = iterative_deepening_search(board, max_depth=6, max_nodes=75)
        assert res.is_interrupted is True
        assert board.fen() == initial_fen
        assert len(board.move_stack) == 0

        # Interrupted search via time limit
        res2 = iterative_deepening_search(board, max_depth=8, time_limit_ms=10.0)
        assert res2.is_interrupted is True
        assert board.fen() == initial_fen
        assert len(board.move_stack) == 0

    def test_board_state_unmutated_after_unexpected_exception(self) -> None:
        """Board must safely unwind all pushed moves even if an unexpected exception occurs."""
        from unittest.mock import patch

        board = chess.Board()
        initial_fen = board.fen()

        with patch("engine.search.alpha_beta.evaluate_position", side_effect=RuntimeError("Simulated failure")):
            with pytest.raises(RuntimeError, match="Simulated failure"):
                alpha_beta_search(board, depth=3)

        assert board.fen() == initial_fen
        assert len(board.move_stack) == 0

    def test_choose_move_routes_iterative_deepening_with_limits(self) -> None:
        """choose_move correctly passes search limits to iterative deepening."""
        board = chess.Board()
        config = SearchConfig(depth=5, algorithm="iterative_deepening", time_limit_ms=25.0)
        res = choose_move(board, config)

        assert res.algorithm == "iterative_deepening"
        assert res.best_move in list(board.legal_moves)
        assert res.is_interrupted is True
        assert res.interruption_reason == "time_limit"

    def test_interrupted_before_depth_1_returns_legal_fallback(self) -> None:
        """When search is aborted before depth 1 can complete, safe legal fallback is returned."""
        board = chess.Board()
        initial_fen = board.fen()

        # Interrupt after 1 node
        res = iterative_deepening_search(board, max_depth=5, max_nodes=1)
        assert res.is_interrupted is True
        assert res.completed_depth == 0
        assert res.best_move is not None
        assert res.best_move in list(board.legal_moves)
        assert board.fen() == initial_fen
        assert len(board.move_stack) == 0

    @pytest.mark.parametrize("diff", ["beginner", "easy", "medium", "hard", "expert"])
    def test_choose_move_with_all_difficulties_returns_legal_move(self, diff: str) -> None:
        """All five difficulty levels return a legal move and restore the board."""
        board = chess.Board()
        initial_fen = board.fen()

        res = choose_move(board, difficulty=diff)
        assert res.best_move is not None
        assert res.best_move in list(board.legal_moves)
        assert res.difficulty == diff
        assert res.allocated_time_ms is not None
        assert res.allocated_time_ms > 0
        assert board.fen() == initial_fen
        assert len(board.move_stack) == 0

    def test_search_determinism_under_same_difficulty(self) -> None:
        """Given identical board and difficulty preset, search produces identical moves."""
        board1 = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5")
        board2 = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5")

        res1 = choose_move(board1, difficulty="easy")
        res2 = choose_move(board2, difficulty="easy")

        assert res1.best_move == res2.best_move
        assert res1.score_cp == res2.score_cp

