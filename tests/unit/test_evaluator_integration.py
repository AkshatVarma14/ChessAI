"""Integration tests for the modular position evaluation system."""

import pytest
import chess

from engine.config import EvaluationConfig
from engine.constants import MATE_SCORE
from engine.evaluation.evaluator import evaluate_position, evaluate_position_breakdown
from engine.search.alpha_beta import alpha_beta_search
from engine.search.minimax import minimax_search


class TestEvaluatorIntegration:
    """Verify component summation, symmetry, terminal overrides, and search integration."""

    def test_breakdown_components_sum_to_total(self) -> None:
        """Every individual component score in the breakdown must sum exactly to total_cp."""
        fens = [
            chess.STARTING_FEN,
            "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1",
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        ]

        for fen in fens:
            board = chess.Board(fen)
            breakdown = evaluate_position_breakdown(board)

            expected_sum = (
                breakdown.material_cp
                + breakdown.pst_cp
                + breakdown.mobility_cp
                + breakdown.pawn_structure_cp
                + breakdown.center_control_cp
                + breakdown.king_safety_cp
                + breakdown.coordination_cp
            )

            assert breakdown.total_cp == expected_sum, f"Sum mismatch on {fen}: {breakdown.total_cp} != {expected_sum}"
            assert evaluate_position(board) == breakdown.total_cp

    def test_terminal_checkmate_overrides_positional_heuristics(self) -> None:
        """Checkmate positions must return ±(MATE_SCORE - ply), bypassing positional terms."""
        # Fool's mate terminal position
        board_mated = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        assert board_mated.is_checkmate()

        score = evaluate_position(board_mated, ply=1)
        assert score == -(MATE_SCORE - 1)

        breakdown = evaluate_position_breakdown(board_mated, ply=1)
        assert breakdown.is_terminal is True
        assert breakdown.terminal_type == "checkmate"
        assert breakdown.total_cp == -(MATE_SCORE - 1)

    def test_terminal_draws_evaluate_to_zero(self) -> None:
        """Stalemate, threefold repetition, and 50-move rule evaluate to 0 cp."""
        # Stalemate
        board_stale = chess.Board("k7/8/1Q6/8/8/8/8/4K3 b - - 0 1")
        assert board_stale.is_stalemate()
        assert evaluate_position(board_stale) == 0

        # Insufficient material
        board_insuf = chess.Board("8/8/8/4k3/8/8/8/4KB2 w - - 0 1")
        assert board_insuf.is_insufficient_material()
        assert evaluate_position(board_insuf) == 0

    def test_mirrored_positions_produce_opposite_scores(self) -> None:
        """Color symmetry: E(pos) == -E(pos.mirror()) across diverse game positions."""
        fens = [
            chess.STARTING_FEN,
            "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1",
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        ]

        for fen in fens:
            board = chess.Board(fen)
            score_pos = evaluate_position(board)
            score_mirrored = evaluate_position(board.mirror())
            assert score_pos == -score_mirrored, f"Symmetry failed on {fen}: {score_pos} != -{score_mirrored}"

    def test_disable_individual_components(self) -> None:
        """Individual evaluation components can be toggled off via EvaluationConfig."""
        board = chess.Board("r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1")

        # Config with only material enabled
        cfg_mat_only = EvaluationConfig(
            use_pst=False,
            use_mobility=False,
            use_pawn_structure=False,
            use_center_control=False,
            use_king_safety=False,
            use_coordination=False,
        )

        breakdown = evaluate_position_breakdown(board, cfg_mat_only)
        assert breakdown.pst_cp == 0
        assert breakdown.mobility_cp == 0
        assert breakdown.pawn_structure_cp == 0
        assert breakdown.center_control_cp == 0
        assert breakdown.king_safety_cp == 0
        assert breakdown.coordination_cp == 0
        assert breakdown.total_cp == breakdown.material_cp

    def test_search_equivalence_with_positional_eval(self) -> None:
        """Minimax and Alpha-Beta return identical scores using the full positional evaluator."""
        fens = [
            chess.STARTING_FEN,
            "4k3/8/8/3r4/4P3/8/8/4K3 w - - 0 1",
            "4k3/8/8/2p5/3Q4/8/8/4K3 b - - 0 1",
        ]

        for fen in fens:
            board = chess.Board(fen)
            mm_res = minimax_search(board, depth=2)
            ab_res = alpha_beta_search(board, depth=2)
            assert ab_res.score_cp == mm_res.score_cp
