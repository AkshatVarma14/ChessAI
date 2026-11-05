"""Unit tests for Alpha-Beta pruning search and Minimax equivalence."""

import pytest
import chess

from engine.constants import MATE_SCORE
from engine.search.alpha_beta import alpha_beta_search
from engine.search.minimax import minimax_search


class TestAlphaBetaPruning:
    """Verify Alpha-Beta pruning mechanics, correctness, and exact Minimax equivalence."""

    def test_board_not_mutated_after_search(self) -> None:
        board = chess.Board()
        initial_fen = board.fen()

        res = alpha_beta_search(board, depth=2)
        assert res.best_move is not None
        assert board.fen() == initial_fen

    @pytest.mark.parametrize("fen", [
        chess.STARTING_FEN,
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        "4k3/8/8/3r4/4P3/8/8/4K3 w - - 0 1",
        "4k3/8/8/2p5/3Q4/8/8/4K3 b - - 0 1",
    ])
    def test_alpha_beta_matches_minimax_score_depth_2(self, fen: str) -> None:
        """Alpha-Beta must produce the exact same minimax score as Minimax at identical depth."""
        board = chess.Board(fen)

        minimax_res = minimax_search(board, depth=2)
        alpha_beta_res = alpha_beta_search(board, depth=2)

        assert alpha_beta_res.score_cp == minimax_res.score_cp
        assert alpha_beta_res.best_move is not None
        assert alpha_beta_res.best_move in list(board.legal_moves)

    def test_alpha_beta_searches_fewer_nodes_than_minimax(self) -> None:
        """Alpha-Beta pruning must achieve branch cutoffs and search fewer nodes than Minimax."""
        # Tactical position with captures
        fen = "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1"
        board = chess.Board(fen)

        minimax_res = minimax_search(board, depth=3)
        alpha_beta_res = alpha_beta_search(board, depth=3)

        assert alpha_beta_res.score_cp == minimax_res.score_cp
        assert alpha_beta_res.nodes_searched < minimax_res.nodes_searched
        assert alpha_beta_res.pruned_nodes > 0

    def test_alpha_beta_finds_mate_in_one(self) -> None:
        fen = "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B5/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4"
        board = chess.Board(fen)

        res = alpha_beta_search(board, depth=2)
        assert res.best_move == chess.Move.from_uci("h5f7")
        assert res.score_cp == MATE_SCORE - 1
        assert res.is_checkmate is True

    def test_alpha_beta_terminal_position_at_root(self) -> None:
        fen_mated = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
        board = chess.Board(fen_mated)

        res = alpha_beta_search(board, depth=2)
        assert res.best_move is None
        assert res.score_cp == -MATE_SCORE
        assert res.is_checkmate is True

    def test_alpha_beta_shorter_forced_mate_preferred(self) -> None:
        """Alpha-Beta prefers immediate checkmate over slower checkmate."""
        fen = "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B5/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4"
        board = chess.Board(fen)

        res = alpha_beta_search(board, depth=3)
        assert res.best_move == chess.Move.from_uci("h5f7")
        assert res.score_cp == MATE_SCORE - 1

    def test_alpha_beta_delaying_unavoidable_mate_preferred(self) -> None:
        """Alpha-Beta correctly chooses line that delays unavoidable mate."""
        fen = "R5k1/3b4/5Q2/8/8/8/8/6K1 b - - 0 1"
        board = chess.Board(fen)

        res = alpha_beta_search(board, depth=4)
        assert res.best_move == chess.Move.from_uci("d7e8")
        assert res.score_cp == MATE_SCORE - 4

    def test_alpha_beta_board_restored_on_search_exception(self) -> None:
        """Board state must be restored if evaluation raises an unexpected exception."""
        from unittest.mock import patch

        board = chess.Board()
        initial_fen = board.fen()

        with patch("engine.search.alpha_beta.evaluate_position", side_effect=RuntimeError("Search error")):
            with pytest.raises(RuntimeError, match="Search error"):
                alpha_beta_search(board, depth=2)

        assert board.fen() == initial_fen
        assert len(board.move_stack) == 0
