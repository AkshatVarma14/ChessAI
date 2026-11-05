"""Unit tests for material heuristic evaluation and score conventions."""

import pytest
import chess

from engine.config import EvaluationConfig
from engine.constants import MATE_SCORE
from engine.evaluation.evaluator import evaluate_position, evaluate_position_breakdown
from engine.evaluation.material import evaluate_material, get_material_breakdown


class TestMaterialEvaluation:
    """Test static material point counting and White-relative sign conventions."""

    def test_starting_position_evaluates_to_zero(self) -> None:
        """Starting position has identical material for White and Black -> 0 cp."""
        board = chess.Board()
        score = evaluate_material(board)
        assert score == 0

    @pytest.mark.parametrize(
        "piece_name,fen,expected_cp",
        [
            ("pawn", "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", 100),
            ("knight", "4k3/8/8/8/8/5N2/8/4K3 w - - 0 1", 320),
            ("bishop", "4k3/8/8/8/2B5/8/8/4K3 w - - 0 1", 330),
            ("rook", "4k3/8/8/8/8/8/8/R3K3 w - - 0 1", 500),
            ("queen", "4k3/8/8/8/8/8/8/3QK3 w - - 0 1", 900),
        ],
    )
    def test_isolated_white_piece_advantages(
        self, piece_name: str, fen: str, expected_cp: int
    ) -> None:
        """Positions where White has exactly one isolated extra piece evaluate to exact centipawn value."""
        board = chess.Board(fen)
        score = evaluate_material(board)
        assert score == expected_cp, f"White extra {piece_name} should evaluate to {expected_cp} cp, got {score}"

    @pytest.mark.parametrize(
        "piece_name,fen,expected_cp",
        [
            ("pawn", "4k3/4p3/8/8/8/8/8/4K3 w - - 0 1", -100),
            ("knight", "4k3/8/5n2/8/8/8/8/4K3 w - - 0 1", -320),
            ("bishop", "4k3/8/8/2b5/8/8/8/4K3 w - - 0 1", -330),
            ("rook", "r3k3/8/8/8/8/8/8/4K3 w - - 0 1", -500),
            ("queen", "3qk3/8/8/8/8/8/8/4K3 w - - 0 1", -900),
        ],
    )
    def test_isolated_black_piece_advantages(
        self, piece_name: str, fen: str, expected_cp: int
    ) -> None:
        """Positions where Black has exactly one isolated extra piece evaluate to negative centipawn value."""
        board = chess.Board(fen)
        score = evaluate_material(board)
        assert score == expected_cp, f"Black extra {piece_name} should evaluate to {expected_cp} cp, got {score}"

    @pytest.mark.parametrize(
        "desc,fen",
        [
            ("Bare kings", "4k3/8/8/8/8/8/8/4K3 w - - 0 1"),
            ("Symmetric pawns", "4k3/4p3/8/8/8/8/4P3/4K3 w - - 0 1"),
            ("Symmetric rooks and knights", "r3k1n1/8/8/8/8/8/8/R3K1N1 w - - 0 1"),
            ("Full symmetric middlegame", "r1b1kbnr/pppp1ppp/2n5/4p3/4P3/2N5/PPPP1PPP/R1B1KBNR w KQkq - 2 3"),
        ],
    )
    def test_balanced_material_evaluates_to_zero(self, desc: str, fen: str) -> None:
        """Any position with equal White and Black material balance must evaluate to exactly 0 cp."""
        board = chess.Board(fen)
        score = evaluate_material(board)
        assert score == 0, f"Balanced position ({desc}) should evaluate to 0 cp, got {score}"

    def test_extra_white_pawn_evaluates_positive(self) -> None:
        """Position where White has an extra pawn on e4 -> +100 cp."""
        board_extra_white_pawn = chess.Board("rnbqkbnr/pppp1ppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        score = evaluate_material(board_extra_white_pawn)
        assert score == 100

    def test_extra_black_queen_evaluates_negative(self) -> None:
        """Position where Black has a queen advantage -> -900 cp."""
        board_no_white_queen = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
        score = evaluate_material(board_no_white_queen)
        assert score == -900

    def test_custom_evaluation_config(self) -> None:
        """Custom configured piece values are respected by evaluator."""
        custom_cfg = EvaluationConfig(
            pawn_value=120,
            knight_value=350,
            bishop_value=360,
            rook_value=550,
            queen_value=1000,
        )
        # White has Rook on e4 vs Black Knight on e5
        board = chess.Board("4k3/8/8/4n3/4R3/8/8/4K3 w - - 0 1")
        score = evaluate_material(board, custom_cfg)
        # Rook (550) - Knight (350) = +200 cp
        assert score == 200

    def test_king_not_counted_as_capturable_material(self) -> None:
        """Positions with only Kings evaluate strictly to 0 cp."""
        board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        assert evaluate_material(board) == 0

    def test_mirrored_positions_produce_opposite_scores(self) -> None:
        """
        Symmetry test: for any position, mirroring the board and swapping colors
        must yield the exact opposite evaluation score (E(mirrored) == -E(pos)).
        """
        # White has an extra Rook and Bishop, Black has an extra Knight
        fen_pos = "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1"
        board = chess.Board(fen_pos)
        score_pos = evaluate_material(board)

        # Mirror board: python-chess board.mirror() inverts ranks and swaps colors
        mirrored_board = board.mirror()
        score_mirrored = evaluate_material(mirrored_board)

        assert score_pos == -score_mirrored

    def test_evaluation_breakdown_consistency(self) -> None:
        """Component breakdown components must sum to the net score."""
        board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        breakdown = get_material_breakdown(board)

        assert breakdown.white_material > 0
        assert breakdown.black_material > 0
        assert breakdown.material_cp == breakdown.white_material - breakdown.black_material
        assert breakdown.total_cp == breakdown.material_cp


class TestTerminalPositionEvaluation:
    """Test checkmate and draw overrides over static material evaluation."""

    def test_white_delivering_checkmate_returns_high_positive(self) -> None:
        # Scholar's mate: Black king is checkmated by White Queen on f7
        fen_mate = "r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        board = chess.Board(fen_mate)
        assert board.is_checkmate()
        assert board.turn == chess.BLACK

        score_ply_0 = evaluate_position(board, ply=0)
        assert score_ply_0 == MATE_SCORE

        # With ply distance 3, score is slightly lower to favor faster mates
        score_ply_3 = evaluate_position(board, ply=3)
        assert score_ply_3 == MATE_SCORE - 3

    def test_black_delivering_checkmate_returns_high_negative(self) -> None:
        # Fool's mate: White king on e1 is checkmated by Black Queen on h4
        fen_mate = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
        board = chess.Board(fen_mate)
        assert board.is_checkmate()
        assert board.turn == chess.WHITE

        score = evaluate_position(board, ply=0)
        assert score == -MATE_SCORE

        score_ply_2 = evaluate_position(board, ply=2)
        assert score == -MATE_SCORE + 0
        assert score_ply_2 == -(MATE_SCORE - 2)

    def test_stalemate_evaluates_to_zero(self) -> None:
        # Stalemate position
        fen_stalemate = "k7/8/1Q6/8/8/8/8/4K3 b - - 0 1"
        board = chess.Board(fen_stalemate)
        assert board.is_stalemate()
        assert evaluate_position(board) == 0

    def test_insufficient_material_evaluates_to_zero(self) -> None:
        board = chess.Board("8/8/8/4k3/8/8/8/4KB2 w - - 0 1")
        assert board.is_insufficient_material()
        assert evaluate_position(board) == 0

    def test_breakdown_reports_terminal_type(self) -> None:
        fen_mate = "r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        board = chess.Board(fen_mate)
        breakdown = evaluate_position_breakdown(board, ply=1)
        assert breakdown.is_terminal is True
        assert breakdown.terminal_type == "checkmate"
        assert breakdown.total_cp == MATE_SCORE - 1

    def test_terminal_scores_override_material(self) -> None:
        """Checkmate score must completely override extreme material deficits."""
        # White has massive material advantage (Queen + Rooks), but Black delivers checkmate
        # Fool's mate setup: White has all original pieces, Black delivered mate with queen
        board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        assert board.is_checkmate()
        material = evaluate_material(board)
        # Material-wise, White has pawns g4, f3 while Black pushed e5 and brought Queen to h4.
        # But evaluate_position must return terminal mate score, NOT material!
        score = evaluate_position(board, ply=1)
        assert score == -(MATE_SCORE - 1)
        assert score != material

    def test_threefold_repetition_evaluates_to_zero(self) -> None:
        """Threefold repetition draw evaluates to exactly 0 cp."""
        board = chess.Board()
        # Create threefold repetition via knights moving back and forth
        moves = ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"]
        for m in moves:
            board.push_san(m)
        assert board.is_repetition(3)
        assert evaluate_position(board) == 0

    def test_fifty_move_rule_evaluates_to_zero(self) -> None:
        """Fifty-move rule draw evaluates to 0 cp."""
        # Position with 100 half-moves (50 full moves) without pawn move or capture
        fen_50 = "4k3/8/8/8/8/8/8/4K2R w - - 100 51"
        board = chess.Board(fen_50)
        assert board.is_fifty_moves()
        assert evaluate_position(board) == 0
