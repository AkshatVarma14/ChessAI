"""Unit tests for piece coordination evaluation."""

import pytest
import chess

from engine.evaluation.coordination import evaluate_coordination


class TestPieceCoordination:
    """Verify bishop pair, open files, 7th rank rooks, and defended piece bonuses."""

    def test_starting_position_coordination_is_zero(self) -> None:
        """Starting position has identical coordination for both sides -> 0 cp."""
        board = chess.Board()
        score = evaluate_coordination(board)
        assert score == 0

    def test_bishop_pair_bonus_awarded(self) -> None:
        """A player holding two bishops receives the bishop pair bonus."""
        # White has Bishop pair (c1, f1), Black has one Bishop and one Knight
        fen = "r1bqk1nr/pppppppp/2n5/8/8/8/PPPPPPPP/RNBQKB1R w KQkq - 0 1"
        board = chess.Board(fen)
        score = evaluate_coordination(board)
        # White has 2 bishops (+30), Black has 1 bishop (0)
        assert score >= 30

    def test_rook_on_open_file_awarded_bonus(self) -> None:
        """A rook on an open file (no pawns) scores higher than a rook behind closed pawns."""
        # e-file is completely open (no pawns); White Rook on e1
        fen = "4k3/pppp1ppp/8/8/8/8/PPPP1PPP/4R1K1 w - - 0 1"
        board = chess.Board(fen)
        score = evaluate_coordination(board)
        # White rook on open e-file (+20 cp)
        assert score >= 20

    def test_rook_on_seventh_rank_awarded_bonus(self) -> None:
        """White rook on the 7th rank (rank index 6) receives an infiltration bonus."""
        fen = "4k3/4R3/8/8/8/8/8/4K3 w - - 0 1"
        board = chess.Board(fen)
        score = evaluate_coordination(board)
        assert score >= 20

    def test_color_symmetry(self) -> None:
        """Mirroring the position inverts the piece coordination score."""
        fen = "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1"
        board = chess.Board(fen)
        score_pos = evaluate_coordination(board)
        score_mirrored = evaluate_coordination(board.mirror())
        assert score_pos == -score_mirrored
