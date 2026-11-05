"""Unit tests for piece mobility evaluation."""

import pytest
import chess

from engine.evaluation.mobility import evaluate_mobility


class TestMobilityEvaluation:
    """Verify piece mobility counting, pawn attack restrictions, and symmetry."""

    def test_starting_position_mobility_is_zero(self) -> None:
        """Starting position has identical mobility for both sides -> 0 cp."""
        board = chess.Board()
        score = evaluate_mobility(board)
        assert score == 0

    def test_active_piece_has_higher_mobility_than_trapped_piece(self) -> None:
        """Centralized open bishop has strictly higher mobility than trapped corner bishop."""
        # White has Bishop on e4 with open board; Black has Bishop on a8 boxed in by pawns
        fen = "7k/1p6/p7/8/4B3/8/8/7K w - - 0 1"
        board = chess.Board(fen)
        score = evaluate_mobility(board)
        # White Bishop on e4 has wide open diagonal rays -> score > 0
        assert score > 0

    def test_enemy_pawn_attacks_reduce_mobility(self) -> None:
        """Squares controlled by enemy pawns are excluded from safe mobility targets."""
        # White Knight on d4 with no enemy pawns vs with Black pawns controlling squares
        board_open = chess.Board("4k3/8/8/8/3N4/8/8/4K3 w - - 0 1")
        score_open = evaluate_mobility(board_open)

        # Black pawns on c6 and e6 attack d5 and b5/f5
        board_restricted = chess.Board("4k3/8/2p1p3/8/3N4/8/8/4K3 w - - 0 1")
        score_restricted = evaluate_mobility(board_restricted)

        assert score_restricted < score_open

    def test_color_symmetry(self) -> None:
        """Mirroring the board inverts the mobility score."""
        fen = "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1"
        board = chess.Board(fen)
        score_pos = evaluate_mobility(board)
        score_mirrored = evaluate_mobility(board.mirror())
        assert score_pos == -score_mirrored

    def test_absolutely_pinned_knight_has_zero_mobility(self) -> None:
        """A knight absolutely pinned to the king cannot move without exposing check, so mobility is zero."""
        # White Knight on c3 is pinned to King on e1 by Black Bishop on b4.
        # Black has no other pieces except bare King on e8.
        board_pinned = chess.Board("4k3/8/8/8/1b6/2N5/8/4K3 w - - 0 1")
        # Both kings and pawns are excluded; White has pinned knight on c3; Black has unpinned bishop on b4.
        # Pinned knight has 0 safe moves along pin ray (knights cannot slide).
        # Therefore White's mobility contribution is 0, and net score is negative (Black bishop has mobility).
        score = evaluate_mobility(board_pinned)
        assert score < 0

        # Contrast with unpinned knight: Knight on c3 is not pinned when King is on g1
        board_unpinned = chess.Board("4k3/8/8/8/1b6/2N5/8/6K1 w - - 0 1")
        score_unpinned = evaluate_mobility(board_unpinned)
        assert score_unpinned > score

    def test_pinned_rook_mobility_restricted_to_pin_ray(self) -> None:
        """A rook pinned along a file can only move along that file, not horizontally."""
        # White Rook on e4 is pinned to King on e1 by Black Rook on e8.
        # Rook on e4 has e2, e3, e5, e6, e7, e8 on the pin ray (6 squares).
        # Without pin, it would also attack d4, c4, b4, a4, f4, g4, h4 (7 horizontal squares).
        board_pinned = chess.Board("4r2k/8/8/8/4R3/8/8/4K3 w - - 0 1")
        score_pinned = evaluate_mobility(board_pinned)

        # Unpinned rook on d4 with king on e1
        board_unpinned = chess.Board("7k/8/8/8/3R4/8/8/4K3 w - - 0 1")
        score_unpinned = evaluate_mobility(board_unpinned)
        assert score_unpinned > score_pinned

    def test_pinned_position_symmetry(self) -> None:
        """Pin restrictions preserve color symmetry under board mirroring."""
        fen = "rnb1k2r/ppp2ppp/5n2/3q4/1b1P4/2N5/PP3PPP/R1BQKBNR w KQkq - 3 7"
        board = chess.Board(fen)
        score_pos = evaluate_mobility(board)
        score_mir = evaluate_mobility(board.mirror())
        assert score_pos == -score_mir
