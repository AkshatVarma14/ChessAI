"""Unit tests for center control and square occupation evaluation."""

import pytest
import chess

from engine.evaluation.center_control import evaluate_center_control


class TestCenterControl:
    """Verify central square occupation, attack influence, and symmetry."""

    def test_starting_position_center_is_zero(self) -> None:
        """Starting position has balanced central tension -> 0 cp."""
        board = chess.Board()
        score = evaluate_center_control(board)
        assert score == 0

    def test_pawn_occupying_center_awarded_bonus(self) -> None:
        """White pawn on e4 vs Black pawn on h7 awards White positive central score."""
        fen = "4k3/7p/8/8/4P3/8/8/4K3 w - - 0 1"
        board = chess.Board(fen)
        score = evaluate_center_control(board)
        assert score > 0

    def test_piece_attacks_on_center_rewarded(self) -> None:
        """White knights developing to f3 and c3 attack d4/e4/d5/e5, yielding central control."""
        # White has knights on c3 and f3 attacking center; Black has knights on a6 and h6 on the rim
        fen = "r1bqkb1r/pppppppp/n6n/8/8/2N2N2/PPPPPPPP/R1BQKB1R w KQkq - 0 1"
        board = chess.Board(fen)
        score = evaluate_center_control(board)
        assert score > 0

    def test_color_symmetry(self) -> None:
        """Mirroring the position inverts the center control evaluation."""
        fen = "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq d3 0 3"
        board = chess.Board(fen)
        score_pos = evaluate_center_control(board)
        score_mirrored = evaluate_center_control(board.mirror())
        assert score_pos == -score_mirrored
