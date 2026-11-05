"""Unit tests for the custom Minimax adversarial search algorithm."""

import pytest
import chess

from engine.config import EvaluationConfig
from engine.constants import MATE_SCORE
from engine.search.minimax import minimax_search


class TestMinimaxSearch:
    """Test Minimax search mechanics, maximization/minimization, and tactical awareness."""

    def test_board_not_mutated_after_search(self) -> None:
        """Minimax must guarantee the root board state is completely restored."""
        board = chess.Board()
        initial_fen = board.fen()

        res = minimax_search(board, depth=2)
        assert res.best_move is not None
        assert board.fen() == initial_fen

    def test_white_maximizes_material(self) -> None:
        """White must choose the move that maximizes material balance."""
        # Initial: White King + Pawn e4 (100 cp), Black King + Rook d5 (500 cp) -> Net: -400 cp.
        # Quiet moves leave White down a rook (-400 cp).
        # White captures the rook with e4xd5:
        # Resulting position has White Pawn (100 cp) vs Black bare King (0 cp) -> Net: +100 cp.
        # White maximizes score -> selects e4d5 yielding +100 cp in material-only mode.
        fen = "4k3/8/8/3r4/4P3/8/8/4K3 w - - 0 1"
        board = chess.Board(fen)

        mat_cfg = EvaluationConfig(
            use_pst=False,
            use_mobility=False,
            use_pawn_structure=False,
            use_center_control=False,
            use_king_safety=False,
            use_coordination=False,
        )

        res = minimax_search(board, depth=2, config=mat_cfg)
        assert res.best_move is not None
        assert res.best_move == chess.Move.from_uci("e4d5")
        assert res.score_cp == 100

        # With full positional evaluation, e4d5 is also chosen with positional bonuses (PST, center, passed pawn)
        pos_res = minimax_search(board, depth=2)
        assert pos_res.best_move == chess.Move.from_uci("e4d5")
        assert pos_res.score_cp > 100

    def test_black_minimizes_material(self) -> None:
        """Black must choose the move that minimizes White-relative material balance."""
        # Initial: White King + Queen d4 (900 cp), Black King + Pawn c5 (100 cp) -> Net: +800 cp.
        # Quiet moves leave Black down a queen (+800 cp for White).
        # Black captures the queen with c5xd4:
        # Resulting position has Black Pawn (100 cp) vs White bare King (0 cp) -> Net: -100 cp (White-relative).
        # Black minimizes score -> selects c5d4 yielding -100 cp in material-only mode.
        fen = "4k3/8/8/2p5/3Q4/8/8/4K3 b - - 0 1"
        board = chess.Board(fen)

        mat_cfg = EvaluationConfig(
            use_pst=False,
            use_mobility=False,
            use_pawn_structure=False,
            use_center_control=False,
            use_king_safety=False,
            use_coordination=False,
        )

        res = minimax_search(board, depth=2, config=mat_cfg)
        assert res.best_move is not None
        assert res.best_move == chess.Move.from_uci("c5d4")
        assert res.score_cp == -100

        # With full positional evaluation, c5d4 is also chosen
        pos_res = minimax_search(board, depth=2)
        assert pos_res.best_move == chess.Move.from_uci("c5d4")
        assert pos_res.score_cp < -100

    def test_white_finds_mate_in_one(self) -> None:
        """White detects and plays immediate checkmate (Scholar's Mate final position)."""
        fen = "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B5/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4"
        board = chess.Board(fen)

        res = minimax_search(board, depth=2)
        assert res.best_move is not None
        assert res.best_move == chess.Move.from_uci("h5f7")
        assert res.is_checkmate is True
        assert res.score_cp == MATE_SCORE - 1  # Mate at ply 1

    def test_shorter_forced_mate_preferred(self) -> None:
        """White must prefer an immediate mate-in-1 over a mate-in-2 line."""
        # Scholar's mate position at depth 3:
        # Immediate mate-in-1: h5f7# (ply 1, score = 29999).
        # Any other moves that may eventually mate score lower due to ply distance penalty.
        fen = "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B5/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4"
        board = chess.Board(fen)

        res = minimax_search(board, depth=3)
        assert res.best_move == chess.Move.from_uci("h5f7")
        assert res.score_cp == MATE_SCORE - 1  # 29999 is preferred over 29997

    def test_delaying_unavoidable_mate_preferred(self) -> None:
        """Black facing unavoidable checkmate must prefer delaying the mate."""
        # White has Rook on a8 checking Black King on g8; Queen on f6 controls escape squares.
        # Black has Bishop on d7.
        # Choice 1: Kh7 allows immediate mate via a8h8# or Qg7# at ply 2 (score 29998).
        # Choice 2: Be8 (d7e8) interposes the Bishop, forcing White to take (ply 2), King runs (ply 3),
        # mate occurs at ply 4 (score 29996).
        # Black (minimizing) prefers 29996 over 29998, choosing d7e8 to delay mate.
        fen = "R5k1/3b4/5Q2/8/8/8/8/6K1 b - - 0 1"
        board = chess.Board(fen)

        res = minimax_search(board, depth=4)
        assert res.best_move == chess.Move.from_uci("d7e8")
        assert res.score_cp == MATE_SCORE - 4  # 29996

    def test_board_restored_on_search_exception(self) -> None:
        """Board state must be restored to its original state even if evaluation raises an error."""
        board = chess.Board()
        initial_fen = board.fen()

        # Invalidate board temporarily inside a mock evaluation
        from unittest.mock import patch

        with patch("engine.search.minimax.evaluate_position", side_effect=RuntimeError("Search error")):
            with pytest.raises(RuntimeError, match="Search error"):
                minimax_search(board, depth=2)

        # Original board remains uncorrupted
        assert board.fen() == initial_fen
        assert len(board.move_stack) == 0

    def test_black_finds_mate_in_one(self) -> None:
        """Black detects and plays immediate checkmate (Fool's Mate final move)."""
        fen = "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2"
        board = chess.Board(fen)

        res = minimax_search(board, depth=2)
        assert res.best_move is not None
        assert res.best_move == chess.Move.from_uci("d8h4")
        assert res.is_checkmate is True
        assert res.score_cp == -(MATE_SCORE - 1)

    def test_checkmate_preferred_over_capturing_material(self) -> None:
        """Engine must prefer delivering checkmate over capturing high-value material."""
        # White can either capture Black's free queen on a8 or play checkmate on f7
        fen = "q1bqkb1r/pppp1ppp/2n5/4p2Q/2B5/8/PPPP1PPP/RNB1K1NR w KQk - 0 4"
        board = chess.Board(fen)

        res = minimax_search(board, depth=2)
        # Checkmate on f7 must be chosen over Queen capture on a8
        assert res.best_move == chess.Move.from_uci("h5f7")
        assert res.score_cp == MATE_SCORE - 1

    def test_terminal_position_at_root(self) -> None:
        """Position where no legal moves exist returns cleanly without error."""
        # Checkmate position (Fool's Mate reached)
        fen_mated = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
        board = chess.Board(fen_mated)
        assert board.is_checkmate()

        res = minimax_search(board, depth=2)
        assert res.best_move is None
        assert res.score_cp == -MATE_SCORE
        assert res.is_checkmate is True

    def test_search_metrics_recorded(self) -> None:
        """Search telemetry (nodes, elapsed time, NPS) is populated accurately."""
        board = chess.Board()
        res = minimax_search(board, depth=2)

        # Depth 2 from starting position: 20 legal moves * 20 responses = 400 leaf nodes + root = 421 total calls
        assert res.nodes_searched > 0
        assert res.depth == 2
        assert res.elapsed_ms >= 0
        assert res.algorithm == "minimax"
        assert res.best_move in list(board.legal_moves)
