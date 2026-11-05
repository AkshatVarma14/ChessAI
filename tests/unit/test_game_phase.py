"""Unit tests for continuous game phase calculation."""

import pytest
import chess

from engine.evaluation.game_phase import calculate_game_phase


class TestGamePhase:
    """Verify phase calculation from opening/middlegame (1.0) to endgame (0.0)."""

    def test_starting_position_phase_is_one(self) -> None:
        """Starting position with all 16 major/minor pieces has phase == 1.0."""
        board = chess.Board()
        phase = calculate_game_phase(board)
        assert phase == 1.0

    def test_bare_kings_phase_is_zero(self) -> None:
        """Positions with only kings (no non-pawn material) have phase == 0.0."""
        board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        assert calculate_game_phase(board) == 0.0

    def test_kings_and_pawns_phase_is_zero(self) -> None:
        """Positions with only kings and pawns have phase == 0.0."""
        board = chess.Board("4k3/pppppppp/8/8/8/8/PPPPPPPP/4K3 w - - 0 1")
        assert calculate_game_phase(board) == 0.0

    def test_queen_endgame_phase(self) -> None:
        """Positions with only Queens and Kings have intermediate phase."""
        # 2 Queens = 4 + 4 = 8 phase points out of 24 -> phase = 8/24 = 0.333
        board = chess.Board("3qk3/8/8/8/8/8/8/3QK3 w - - 0 1")
        phase = calculate_game_phase(board)
        assert abs(phase - (8.0 / 24.0)) < 1e-4

    def test_smooth_monotonic_transitions(self) -> None:
        """Removing non-pawn pieces strictly reduces the game phase."""
        board = chess.Board()
        initial_phase = calculate_game_phase(board)

        # Remove queen from d1
        board.remove_piece_at(chess.D1)
        phase_minus_queen = calculate_game_phase(board)
        assert phase_minus_queen < initial_phase

        # Remove rook from a1
        board.remove_piece_at(chess.A1)
        phase_minus_rook = calculate_game_phase(board)
        assert phase_minus_rook < phase_minus_queen

    def test_color_symmetry(self) -> None:
        """Mirroring the board preserves the exact same game phase."""
        fen = "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1"
        board = chess.Board(fen)
        assert calculate_game_phase(board) == calculate_game_phase(board.mirror())
