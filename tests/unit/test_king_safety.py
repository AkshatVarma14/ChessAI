"""Unit tests for king safety evaluation."""

import pytest
import chess

from engine.evaluation.king_safety import evaluate_king_safety


class TestKingSafety:
    """Verify pawn shield, open file penalties, and endgame tapering."""

    def test_starting_position_king_safety_is_zero(self) -> None:
        """Both sides have intact pawn shields and equal safety -> 0 cp."""
        board = chess.Board()
        score = evaluate_king_safety(board, phase=1.0)
        assert score == 0

    def test_missing_pawn_shield_penalized(self) -> None:
        """Castled king with missing g-pawn shield is penalized compared to intact shield."""
        # White has castled King on g1 with f2, g2, h2 intact.
        # Black has castled King on g8 with f7, h7 but g7 is missing (semi-open file towards King).
        fen = "5rk1/5p1p/8/8/8/8/5PPP/5RK1 w - - 0 1"
        board = chess.Board(fen)
        score = evaluate_king_safety(board, phase=1.0)
        # White has intact shield, Black has broken shield -> score favors White (> 0)
        assert score > 0

    def test_king_zone_attacks_penalized(self) -> None:
        """Enemy pieces bearing down on the king zone increase defensive penalty."""
        # Black Queen on g3 attacking f2/g2/h2 squares
        fen_attacked = "7k/5ppp/8/8/8/6q1/5PPP/5RK1 w - - 0 1"
        board = chess.Board(fen_attacked)
        score = evaluate_king_safety(board, phase=0.8)
        assert score < 0  # White King under attack -> favors Black

    def test_endgame_phase_drops_king_safety_penalty(self) -> None:
        """In pure endgame (phase=0.0), king safety is not penalized to allow king activation."""
        # Exposed king in endgame
        fen = "4k3/8/8/4K3/8/8/8/8 w - - 0 1"
        board = chess.Board(fen)
        score = evaluate_king_safety(board, phase=0.0)
        assert score == 0

    def test_color_symmetry(self) -> None:
        """Mirroring the position inverts the king safety score."""
        fen = "r1bq1rk1/pppp1ppp/2n5/8/8/2N5/PPPP1PPP/R1BQ1RK1 w - - 0 1"
        board = chess.Board(fen)
        score_pos = evaluate_king_safety(board, phase=0.9)
        score_mirrored = evaluate_king_safety(board.mirror(), phase=0.9)
        assert score_pos == -score_mirrored
