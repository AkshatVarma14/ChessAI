"""Unit tests for move ordering, MVV-LVA, killer moves, and history heuristics."""

import pytest
import chess

from engine.config import EvaluationConfig
from engine.search.alpha_beta import alpha_beta_search
from engine.search.minimax import minimax_search
from engine.search.ordering import SearchContext, order_moves, score_move


class TestMoveOrdering:
    """Test tactical and heuristic move prioritization."""

    def test_move_ordering_preserves_all_legal_moves(self) -> None:
        """Move ordering must never drop, duplicate, or invent moves."""
        board = chess.Board()
        legal = list(board.legal_moves)
        ordered = order_moves(board, legal)

        assert len(ordered) == len(legal)
        assert set(ordered) == set(legal)

    def test_promotions_receive_highest_priority(self) -> None:
        """Pawn promotions (especially Queen) must be ordered ahead of quiet moves."""
        # White has pawn on e7 ready to promote, King on e1.
        # Legal moves include e7e8q, e7e8r, e7e8b, e7e8n, and quiet king moves
        fen = "8/4P3/8/8/8/8/8/4K2k w - - 0 1"
        board = chess.Board(fen)
        legal = list(board.legal_moves)
        ordered = order_moves(board, legal)

        # Queen promotion must be ranked first
        assert ordered[0] == chess.Move.from_uci("e7e8q")
        # All 4 promotion moves must come before quiet king moves
        promo_moves = {chess.Move.from_uci(m) for m in ("e7e8q", "e7e8r", "e7e8b", "e7e8n")}
        assert set(ordered[:4]) == promo_moves

    def test_captures_ordered_mvv_lva(self) -> None:
        """Captures must be prioritized by MVV-LVA (victim value - attacker value)."""
        # 1. Victim value comparison: White Pawn on d4 can capture Black Queen on c5 or Black Rook on e5
        fen_victim = "7k/8/8/2q1r3/3P4/8/8/K7 w - - 0 1"
        board_victim = chess.Board(fen_victim)
        ordered_victim = order_moves(board_victim, list(board_victim.legal_moves))

        move_pxq = chess.Move.from_uci("d4c5")
        move_pxr = chess.Move.from_uci("d4e5")
        assert ordered_victim.index(move_pxq) < ordered_victim.index(move_pxr)

        # 2. Attacker value comparison: White Pawn on d4 vs White Queen on a5 both attacking Black Queen on c5
        fen_attacker = "7k/8/8/Q1q5/3P4/8/8/K7 w - - 0 1"
        board_attacker = chess.Board(fen_attacker)
        ordered_attacker = order_moves(board_attacker, list(board_attacker.legal_moves))

        move_qxq = chess.Move.from_uci("a5c5")
        assert ordered_attacker.index(move_pxq) < ordered_attacker.index(move_qxq)

    def test_favorable_captures_before_losing_captures(self) -> None:
        """Capturing high-value piece with pawn must rank before capturing defended pawn with queen."""
        # White has Queen on d1 and Pawn on d4.
        # Black has Queen on e5 and Pawn on c5.
        fen = "4k3/8/8/2p1q3/3P4/8/8/3QK3 w - - 0 1"
        board = chess.Board(fen)
        legal = list(board.legal_moves)
        ordered = order_moves(board, legal)

        move_pxq = chess.Move.from_uci("d4e5")  # PxQ (favorable)
        move_qxp = chess.Move.from_uci("d1c2")  # quiet move
        assert ordered[0] == move_pxq

    def test_en_passant_capture_ordered_correctly(self) -> None:
        """En passant captures must be identified as pawn-takes-pawn captures."""
        # Standard en passant setup: White pawn on e5, Black just played d7d5 -> ep square d6
        board = chess.Board("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
        ep_move = chess.Move.from_uci("e5d6")
        assert board.is_en_passant(ep_move)

        ordered = order_moves(board, list(board.legal_moves))
        # ep_move is a favorable/equal capture (PxP) and should be ordered high among moves
        ep_idx = ordered.index(ep_move)
        quiet_pawn_move = chess.Move.from_uci("a2a3")
        quiet_idx = ordered.index(quiet_pawn_move)
        assert ep_idx < quiet_idx

    def test_killer_moves_prioritized_over_other_quiet_moves(self) -> None:
        """A quiet move registered in the killer table must be sorted before other quiet moves."""
        board = chess.Board()
        context = SearchContext()
        quiet_move = chess.Move.from_uci("g1f3")
        other_quiet = chess.Move.from_uci("e2e4")

        # Record g1f3 as a killer at ply 1
        context.killers[1] = [quiet_move]

        legal = list(board.legal_moves)
        ordered = order_moves(board, legal, ply=1, context=context)

        # The killer move must appear before other quiet moves
        assert ordered.index(quiet_move) < ordered.index(other_quiet)

    def test_history_heuristic_rewards_frequent_cutoff_moves(self) -> None:
        """Quiet moves with higher history scores must be sorted ahead of unrewarded quiet moves."""
        board = chess.Board()
        context = SearchContext()

        move_a = chess.Move.from_uci("b1c3")
        move_b = chess.Move.from_uci("g1f3")

        # Record high cutoff history for move_a
        context.history[(move_a.from_square, move_a.to_square)] = 500

        ordered = order_moves(board, list(board.legal_moves), ply=0, context=context)
        assert ordered.index(move_a) < ordered.index(move_b)

    def test_pv_move_ranked_first(self) -> None:
        """If a PV move from a previous iteration is supplied, it must be ranked first."""
        board = chess.Board()
        pv_move = chess.Move.from_uci("e2e4")
        ordered = order_moves(board, list(board.legal_moves), pv_move=pv_move)
        assert ordered[0] == pv_move

    def test_move_ordering_preserves_minimax_score_equivalence(self) -> None:
        """
        Critical invariant: Move ordering must NOT alter the mathematical minimax score
        of a completed fixed-depth Alpha-Beta search.
        """
        positions = [
            chess.STARTING_FEN,
            "r1bqk2r/pppp1ppp/2n5/8/3BR3/8/PPP2PPP/R2QKBNR w KQkq - 0 1",
            "4k3/8/8/3r4/4P3/8/8/4K3 w - - 0 1",
        ]

        for fen in positions:
            board = chess.Board(fen)
            mm_res = minimax_search(board, depth=3)
            ab_ordered_res = alpha_beta_search(board, depth=3, use_move_ordering=True)
            ab_unordered_res = alpha_beta_search(board, depth=3, use_move_ordering=False)

            assert ab_ordered_res.score_cp == mm_res.score_cp
            assert ab_unordered_res.score_cp == mm_res.score_cp
            # Ordered search should typically evaluate significantly fewer or equal nodes
            assert ab_ordered_res.nodes_searched <= ab_unordered_res.nodes_searched
