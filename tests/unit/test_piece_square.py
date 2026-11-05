"""Unit tests for Piece-Square Table (PST) positional bonuses."""

import pytest
import chess

from engine.evaluation.piece_square import (
    evaluate_piece_square,
    get_piece_square_score,
    KNIGHT_TABLE,
    PAWN_TABLE,
    KING_TABLE_MG,
    KING_TABLE_EG,
)


class TestPieceSquareTables:
    """Verify PST orientation, color mirroring, and strategic preferences."""

    def test_pawn_table_orientation(self) -> None:
        """Pawns on rank 7 have higher positional bonuses than rank 2."""
        # e2 (rank 2, file 4 = index 12) vs e7 (rank 7, file 4 = index 52)
        score_e2 = PAWN_TABLE[chess.E2]
        score_e7 = PAWN_TABLE[chess.E7]
        assert score_e7 > score_e2

    def test_knight_centralization_preferred(self) -> None:
        """Knights on central outposts (e4/d4) score higher than rim squares (a1/h1/a8)."""
        score_center = KNIGHT_TABLE[chess.E4]
        score_rim = KNIGHT_TABLE[chess.A1]
        assert score_center > score_rim
        assert score_center > KNIGHT_TABLE[chess.H1]
        assert score_center > KNIGHT_TABLE[chess.A8]

    def test_color_mirroring_symmetry(self) -> None:
        """
        Symmetry test: for any position, mirroring the board (inverted ranks, swapped colors)
        must yield the exact opposite PST score: E(mirrored) == -E(pos).
        """
        fens = [
            chess.STARTING_FEN,
            "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1",
            "4k3/8/8/3r4/4P3/8/8/4K3 w - - 0 1",
            "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        ]

        for fen in fens:
            board = chess.Board(fen)
            score_pos = evaluate_piece_square(board, phase=0.8)
            score_mirrored = evaluate_piece_square(board.mirror(), phase=0.8)
            assert score_pos == -score_mirrored

    def test_starting_position_pst_is_zero(self) -> None:
        """Starting position is completely symmetric -> 0 cp PST."""
        board = chess.Board()
        score = evaluate_piece_square(board, phase=1.0)
        assert score == 0

    def test_king_table_tapered_switch(self) -> None:
        """In the middlegame, castled King on g1 is favored; in the endgame, central King is favored."""
        # In middlegame (phase=1.0)
        mg_g1 = get_piece_square_score(chess.KING, chess.G1, phase=1.0)
        mg_e4 = get_piece_square_score(chess.KING, chess.E4, phase=1.0)
        assert mg_g1 > mg_e4  # Castled g1 preferred over central e4 in middlegame

        # In endgame (phase=0.0)
        eg_g1 = get_piece_square_score(chess.KING, chess.G1, phase=0.0)
        eg_e4 = get_piece_square_score(chess.KING, chess.E4, phase=0.0)
        assert eg_e4 > eg_g1  # Central e4 preferred over corner g1 in endgame
