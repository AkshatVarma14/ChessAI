"""Unit tests for independent pawn structure features."""

import pytest
import chess

from engine.evaluation.pawn_structure import evaluate_pawn_structure


class TestPawnStructure:
    """Verify passed, isolated, doubled, and connected pawn heuristics."""

    def test_starting_position_pawn_structure_is_zero(self) -> None:
        """Standard starting position has symmetric pawn chains -> 0 cp."""
        board = chess.Board()
        score = evaluate_pawn_structure(board)
        assert score == 0

    def test_passed_pawn_awarded_bonus(self) -> None:
        """A passed pawn without opposing enemy pawns receives advancement bonus."""
        # White has passed pawn on e5 (rank 5); Black has no pawns on d, e, f files
        fen = "4k3/8/8/4P3/8/8/8/4K3 w - - 0 1"
        board = chess.Board(fen)
        score = evaluate_pawn_structure(board, phase=0.0)
        assert score > 0

    def test_passed_pawn_advancement_scales(self) -> None:
        """Passed pawn on rank 6 scores higher than passed pawn on rank 3."""
        board_r3 = chess.Board("4k3/8/8/8/8/4P3/8/4K3 w - - 0 1")
        board_r6 = chess.Board("4k3/8/4P3/8/8/8/8/4K3 w - - 0 1")

        score_r3 = evaluate_pawn_structure(board_r3, phase=0.5)
        score_r6 = evaluate_pawn_structure(board_r6, phase=0.5)
        assert score_r6 > score_r3

    def test_isolated_pawn_penalized(self) -> None:
        """A pawn with no friendly pawns on adjacent files is penalized."""
        # White has pawns on a2 and c2; pawn on a2 is isolated because no pawn on b-file
        # Compare to connected pawns on a2 and b2
        board_isolated = chess.Board("4k3/8/8/8/8/8/P1P5/4K3 w - - 0 1")
        board_connected = chess.Board("4k3/8/8/8/8/8/PP6/4K3 w - - 0 1")

        score_isolated = evaluate_pawn_structure(board_isolated)
        score_connected = evaluate_pawn_structure(board_connected)
        assert score_isolated < score_connected

    def test_doubled_pawns_penalized(self) -> None:
        """Two pawns stacked on the same file receive a doubled pawn penalty."""
        # White has doubled pawns on e3 and e4 vs pawns on d3 and e4
        board_doubled = chess.Board("4k3/8/8/8/4P3/4P3/8/4K3 w - - 0 1")
        board_normal = chess.Board("4k3/8/8/8/4P3/3P4/8/4K3 w - - 0 1")

        score_doubled = evaluate_pawn_structure(board_doubled)
        score_normal = evaluate_pawn_structure(board_normal)
        assert score_doubled < score_normal

    def test_multi_feature_independence(self) -> None:
        """
        In accordance with project rules, a pawn can simultaneously be isolated and passed.
        Both terms must be accounted for without short-circuiting.
        """
        # White lone pawn on e6 is isolated (no pawns on d/f) AND passed (no Black pawns)
        board = chess.Board("4k3/8/4P3/8/8/8/8/4K3 w - - 0 1")
        score = evaluate_pawn_structure(board, phase=0.0)
        # Passed pawn bonus (+110) minus isolated penalty (-15) -> positive score
        assert score > 50

    def test_color_symmetry(self) -> None:
        """Mirroring the position inverts the pawn structure score."""
        fen = "r1bqk2r/ppp2ppp/2n5/3pP3/3P4/5N2/PPP2PPP/R1BQKB1R w KQkq - 0 8"
        board = chess.Board(fen)
        score_pos = evaluate_pawn_structure(board)
        score_mirrored = evaluate_pawn_structure(board.mirror())
        assert score_pos == -score_mirrored
