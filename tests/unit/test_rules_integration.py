"""Unit tests for chess rules integration via python-chess."""

import pytest
import chess

from backend.game.exceptions import IllegalMoveError
from backend.game.service import Game


def perft(board: chess.Board, depth: int) -> int:
    """Helper to compute perft (leaf node count) using python-chess legal moves."""
    if depth == 0:
        return 1
    nodes = 0
    for move in board.legal_moves:
        board.push(move)
        nodes += perft(board, depth - 1)
        board.pop()
    return nodes


class TestPerftValidation:
    """Validate perft counts against established reference values."""

    def test_perft_starting_position_depth_1_to_3(self) -> None:
        """Starting position: Depth 1=20, Depth 2=400, Depth 3=8,902."""
        board = chess.Board()
        assert perft(board, 1) == 20
        assert perft(board, 2) == 400
        assert perft(board, 3) == 8902

    def test_perft_kiwipete_depth_1_and_2(self) -> None:
        """Kiwipete position (rich in pins, checks, promotions): Depth 1=48, Depth 2=2,039."""
        kiwipete_fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -"
        board = chess.Board(kiwipete_fen)
        assert perft(board, 1) == 48
        assert perft(board, 2) == 2039


class TestBasicMoveLegality:
    """Test standard piece and pawn movement."""

    def test_starting_position_move_counts(self) -> None:
        game = Game("test-starting")
        # 16 pawn moves (8 single + 8 double) + 4 knight moves = 20
        assert len(game.get_legal_moves_uci()) == 20
        assert game.turn == "white"
        assert not game.is_check
        assert not game.is_terminal
        assert game.status == "active"
        assert game.result == "*"

    def test_legal_pawn_pushes(self) -> None:
        game = Game("test-pawn")
        # Single push
        rec1 = game.apply_move("e4")
        assert rec1.san == "e4"
        assert rec1.uci == "e2e4"
        assert game.turn == "black"

        # Black double push
        rec2 = game.apply_move("e5")
        assert rec2.san == "e5"
        assert rec2.uci == "e7e5"
        assert game.turn == "white"

    def test_illegal_moves_rejected(self) -> None:
        game = Game("test-illegal")
        # Pawn cannot move 3 squares
        with pytest.raises(IllegalMoveError):
            game.apply_move("e2e5")

        # Moving opponent piece on White's turn
        with pytest.raises(IllegalMoveError):
            game.apply_move("e7e5")

        # Moving through blocking piece (e.g. bishop through pawns)
        with pytest.raises(IllegalMoveError):
            game.apply_move("Bc4")


class TestCastlingRules:
    """Test kingside and queenside castling rules and restrictions."""

    def test_kingside_castling(self) -> None:
        # Position ready for White kingside castling: White king on e1, Rook on h1, path clear
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQK2R w KQkq - 0 1"
        game = Game("test-castle-k", initial_fen=fen)
        record = game.apply_move("O-O")
        assert record.san == "O-O"
        assert record.uci == "e1g1"
        assert "RNBQ1RK1" in game.fen

    def test_queenside_castling(self) -> None:
        # Position ready for White queenside castling: White king on e1, Rook on a1, path clear
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/R3KBNR w KQkq - 0 1"
        game = Game("test-castle-q", initial_fen=fen)
        record = game.apply_move("O-O-O")
        assert record.san == "O-O-O"
        assert record.uci == "e1c1"

    def test_castling_prevented_when_in_check(self) -> None:
        # White king on e1 is in check from black rook on e8
        fen = "4r3/8/8/8/8/8/4P3/R3K2R w KQ - 0 1"
        # Move rook to check position
        fen_in_check = "4r3/8/8/8/8/8/8/R3K2R w KQ - 0 1"
        game = Game("test-castle-check", initial_fen=fen_in_check)
        assert game.is_check
        with pytest.raises(IllegalMoveError):
            game.apply_move("O-O")
        with pytest.raises(IllegalMoveError):
            game.apply_move("O-O-O")

    def test_castling_prevented_through_check(self) -> None:
        # Transit square f1 is attacked by black rook on f8
        fen = "5r2/8/8/8/8/8/8/R3K2R w KQ - 0 1"
        game = Game("test-castle-transit", initial_fen=fen)
        assert not game.is_check
        # f1 is attacked, kingside castling illegal
        with pytest.raises(IllegalMoveError):
            game.apply_move("O-O")
        # Queenside is not attacked and should be legal
        rec = game.apply_move("O-O-O")
        assert rec.san == "O-O-O"

    def test_castling_prevented_after_king_moved(self) -> None:
        # FEN with no castling rights (rights lost after King moved)
        fen = "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1"
        game = Game("test-no-rights", initial_fen=fen)
        with pytest.raises(IllegalMoveError):
            game.apply_move("O-O")


class TestEnPassantRules:
    """Test en passant captures and expiry."""

    def test_valid_en_passant(self) -> None:
        # Position after 1. e4 c6 2. e5: Black plays d7-d5 -> White can capture exd6 e.p.
        fen = "rnbqkbnr/pp1ppppp/2p5/4P3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2"
        game = Game("test-ep", initial_fen=fen)
        game.apply_move("d5")
        assert game.fen.endswith("d6 0 3")

        # White captures en passant
        record = game.apply_move("exd6")
        assert record.is_capture
        assert record.san == "exd6"
        assert record.uci == "e5d6"

    def test_en_passant_expires_after_one_move(self) -> None:
        fen = "rnbqkbnr/pp1ppppp/2p5/4P3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2"
        game = Game("test-ep-expiry", initial_fen=fen)
        game.apply_move("d5")  # Black double push
        # White plays another move instead of en passant
        game.apply_move("Nf3")
        # Black plays a quiet move
        game.apply_move("Nf6")
        # White can no longer play exd6
        with pytest.raises(IllegalMoveError):
            game.apply_move("exd6")


class TestPawnPromotion:
    """Test all four promotion options (Queen, Rook, Bishop, Knight)."""

    def test_promotion_to_all_pieces(self) -> None:
        for piece, san_suffix in [("q", "Q"), ("r", "R"), ("b", "B"), ("n", "N")]:
            fen = "8/4P3/8/8/8/8/k7/4K3 w - - 0 1"
            game = Game(f"test-promo-{piece}", initial_fen=fen)
            record = game.apply_move(f"e7e8{piece}")
            assert record.promotion == piece
            assert record.san == f"e8={san_suffix}"
            assert game.turn == "black"

    def test_promotion_without_piece_specifier_is_rejected(self) -> None:
        fen = "8/4P3/8/8/8/8/k7/4K3 w - - 0 1"
        game = Game("test-promo-missing", initial_fen=fen)
        with pytest.raises(IllegalMoveError):
            game.apply_move("e7e8")


class TestChecksAndPins:
    """Test check evasions, pinned piece restrictions, and king safety."""

    def test_pinned_piece_cannot_move(self) -> None:
        # White king on e1, White knight on e2, Black rook on e8 -> Knight is absolutely pinned
        fen = "4r3/8/8/8/8/8/4N3/4K3 w - - 0 1"
        game = Game("test-pin", initial_fen=fen)
        # Knight moving off the e-file exposing king to check is illegal
        with pytest.raises(IllegalMoveError):
            game.apply_move("Nd4")
        with pytest.raises(IllegalMoveError):
            game.apply_move("Nf4")

    def test_check_must_be_evaded(self) -> None:
        # White king on e1 is in check from black queen on e4
        fen = "8/8/8/8/4q3/8/8/R3K2R w KQ - 0 1"
        game = Game("test-check-evade", initial_fen=fen)
        assert game.is_check
        # Moving rook a1-d1 does not resolve check -> illegal
        with pytest.raises(IllegalMoveError):
            game.apply_move("Rad1")
        # King moving to d1 resolves check -> legal
        rec = game.apply_move("Kd1")
        assert not game.is_check


class TestTerminalConditions:
    """Test checkmate, stalemate, insufficient material, repetition, 50-move rule."""

    def test_fools_mate(self) -> None:
        """Fool's Mate: 1. f3 e5 2. g4 Qh4#."""
        game = Game("test-fools-mate")
        game.apply_move("f3")
        game.apply_move("e5")
        game.apply_move("g4")
        rec = game.apply_move("Qh4#")
        assert rec.is_check
        assert game.is_terminal
        assert game.status == "checkmate"
        assert game.result == "0-1"

    def test_stalemate(self) -> None:
        # Standard stalemate position: Black king on a8 has no legal moves, not in check
        fen = "k7/8/1Q6/8/8/8/8/4K3 b - - 0 1"
        game = Game("test-stalemate", initial_fen=fen)
        assert not game.is_check
        assert game.is_terminal
        assert game.status == "stalemate"
        assert game.result == "1/2-1/2"

    def test_insufficient_material_king_vs_king(self) -> None:
        fen = "8/8/8/4k3/8/8/8/4K3 w - - 0 1"
        game = Game("test-insufficient-kk", initial_fen=fen)
        assert game.is_terminal
        assert game.status == "draw_insufficient_material"
        assert game.result == "1/2-1/2"

    def test_insufficient_material_king_bishop_vs_king(self) -> None:
        fen = "8/8/8/4k3/8/8/8/4KB2 w - - 0 1"
        game = Game("test-insufficient-kbk", initial_fen=fen)
        assert game.is_terminal
        assert game.status == "draw_insufficient_material"
        assert game.result == "1/2-1/2"

    def test_threefold_repetition(self) -> None:
        game = Game("test-repetition")
        # Knights oscillate back and forth
        moves = [
            "Nf3", "Nf6", "Ng1", "Ng8",  # 2nd occurrence of starting position
            "Nf3", "Nf6", "Ng1", "Ng8",  # 3rd occurrence of starting position
        ]
        for m in moves:
            game.apply_move(m)

        # Threefold repetition is claimable, NOT automatically terminal
        assert not game.is_terminal
        assert game.can_claim_draw is True
        assert game.claimable_draw == "threefold_repetition"
        assert game.status == "active"
        assert game.result == "*"

        # Further moves can still be played
        game.apply_move("e4")
        assert game.can_claim_draw is False
        assert not game.is_terminal

    def test_claim_draw_threefold_repetition(self) -> None:
        game = Game("test-claim-repetition")
        moves = [
            "Nf3", "Nf6", "Ng1", "Ng8",
            "Nf3", "Nf6", "Ng1", "Ng8",
        ]
        for m in moves:
            game.apply_move(m)

        # Claim the draw
        reason = game.claim_draw()
        assert reason == "draw_repetition"
        assert game.is_terminal
        assert game.status == "draw_repetition"
        assert game.result == "1/2-1/2"

    def test_fivefold_repetition_automatic_termination(self) -> None:
        game = Game("test-fivefold-repetition")
        moves = [
            "Nf3", "Nf6", "Ng1", "Ng8",  # 2nd
            "Nf3", "Nf6", "Ng1", "Ng8",  # 3rd
            "Nf3", "Nf6", "Ng1", "Ng8",  # 4th
            "Nf3", "Nf6", "Ng1", "Ng8",  # 5th occurrence
        ]
        for m in moves:
            game.apply_move(m)

        # Fivefold repetition is automatically terminal
        assert game.is_terminal
        assert game.status == "draw_fivefold_repetition"
        assert game.result == "1/2-1/2"

    def test_fifty_move_rule(self) -> None:
        # FEN with rooks (sufficient material) and halfmove clock at 99 (one move away from 50 full moves)
        fen = "r3k3/8/8/8/8/8/8/4K2R w K - 99 50"
        game = Game("test-50-moves", initial_fen=fen)
        assert not game.is_terminal
        # Quiet king move reaches 100 half-moves
        game.apply_move("Kd1")
        # 50-move rule is claimable, NOT automatically terminal
        assert not game.is_terminal
        assert game.can_claim_draw is True
        assert game.claimable_draw == "fifty_moves"
        assert game.status == "active"
        assert game.result == "*"

        # Claim the draw
        reason = game.claim_draw()
        assert reason == "draw_50_moves"
        assert game.is_terminal
        assert game.status == "draw_50_moves"
        assert game.result == "1/2-1/2"

    def test_seventy_five_move_rule_automatic_termination(self) -> None:
        # FEN with halfmove clock at 149 (one move away from 75 full moves)
        fen = "r3k3/8/8/8/8/8/8/4K2R w K - 149 75"
        game = Game("test-75-moves", initial_fen=fen)
        assert not game.is_terminal
        # Quiet king move reaches 150 half-moves
        game.apply_move("Kd1")
        assert game.is_terminal
        assert game.status == "draw_75_moves"
        assert game.result == "1/2-1/2"
