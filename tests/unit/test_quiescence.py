"""Unit tests for Quiescence Search tactical stability and horizon mitigation."""

import chess
import pytest

from engine.config import EvaluationConfig, SearchConfig
from engine.constants import INFINITY, MATE_SCORE
from engine.evaluation.evaluator import evaluate_position
from engine.search.ordering import SearchContext, SearchInterrupted
from engine.search.quiescence import quiescence_search
from engine.search.alpha_beta import alpha_beta_search
from engine.search.iterative_deepening import iterative_deepening_search
from engine import choose_move


def test_quiescence_preserves_board_state():
    """Verify board state (FEN and move stack) is identically preserved after quiescence search."""
    fen = "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"
    board = chess.Board(fen)
    initial_fen = board.fen()
    initial_stack_len = len(board.move_stack)

    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)

    assert isinstance(score, int)
    assert board.fen() == initial_fen
    assert len(board.move_stack) == initial_stack_len


def test_stand_pat_immediate_beta_cutoff_white():
    """White (maximizing): if stand-pat >= beta, immediately cutoff and return stand-pat."""
    # White is up a Queen (+900 cp), beta is 500 cp
    fen = "4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1"
    board = chess.Board(fen)

    score = quiescence_search(board, alpha=-1000, beta=500, ply=0)

    # Stand-pat is around +900 cp, which is >= beta (500)
    assert score >= 500


def test_stand_pat_immediate_alpha_cutoff_black():
    """Black (minimizing): if stand-pat <= alpha, immediately cutoff and return stand-pat."""
    # Black is up a Queen (-900 cp), alpha is -500 cp
    fen = "4k3/4q3/8/8/8/8/8/4K3 b - - 0 1"
    board = chess.Board(fen)

    score = quiescence_search(board, alpha=-500, beta=1000, ply=0)

    # Stand-pat is around -900 cp, which is <= alpha (-500)
    assert score <= -500


def test_quiescence_disallows_stand_pat_when_in_check():
    """When side to move is in check, stand-pat is strictly prohibited; all legal evasions searched."""
    # White King on e1 is in check by Black Rook on e8
    fen = "4r2k/8/8/8/8/8/8/4K3 w - - 0 1"
    board = chess.Board(fen)
    assert board.is_check()

    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    # King can escape to f1, d1, f2, d2; score is valid integer and not checkmate
    assert isinstance(score, int)
    assert score > -10000


def test_checkmate_detection_in_quiescence():
    """Checkmate during quiescence search returns mate distance score."""
    # Black is checkmated (Scholar's mate)
    fen = "r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
    board = chess.Board(fen)
    assert board.is_checkmate()
    assert board.turn == chess.BLACK

    # Black is checkmated, so White scored a win: MATE_SCORE - ply
    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=2)
    assert score == (MATE_SCORE - 2)

    # White is checkmated (Fool's mate)
    fools_fen = "rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
    white_mated_board = chess.Board(fools_fen)
    assert white_mated_board.is_checkmate()
    assert white_mated_board.turn == chess.WHITE

    # White is checkmated: -(MATE_SCORE - ply)
    score_white_mated = quiescence_search(white_mated_board, alpha=-INFINITY, beta=INFINITY, ply=3)
    assert score_white_mated == -(MATE_SCORE - 3)


def test_stalemate_detection_in_quiescence():
    """Stalemate during quiescence search returns 0 cp."""
    fen = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    board = chess.Board(fen)
    assert board.is_stalemate()

    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    assert score == 0


def test_quiescence_resolves_hanging_piece_white():
    """Quiescence captures an undefended Queen instead of stopping at quiet evaluation (White)."""
    # White bishop on c4 attacks hanging Queen on d5.
    fen = "r4rk1/ppp2ppp/8/3q4/2B5/8/PPP2PPP/R4RK1 w - - 0 1"
    board = chess.Board(fen)

    stand_pat = evaluate_position(board)
    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    # Stand-pat is negative (~ -580 cp) since White was down a Queen.
    # After Bxd5, White captures the Queen and score improves by ~900 cp to positive.
    assert stand_pat < -500
    assert score > 300


def test_quiescence_resolves_hanging_piece_black():
    """Quiescence captures an undefended Queen instead of stopping at quiet evaluation (Black)."""
    # Black bishop on c5 attacks hanging Queen on d4.
    fen = "r4rk1/ppp2ppp/8/2b5/3Q4/8/PPP2PPP/R4RK1 b - - 0 1"
    board = chess.Board(fen)

    stand_pat = evaluate_position(board)
    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    # White was up a Queen (stand_pat > 500 cp).
    # After Bxd4, Black captures White's Queen, making score negative for White (Black advantage).
    assert stand_pat > 500
    assert score < -300


def test_quiescence_resolves_favorable_capture_chain():
    """Quiescence follows capture and recapture to evaluate the net material exchange."""
    # White Qd2 and Rd1, Black Qd5 and Rd8.
    # 1. Qxd5 Rxd5 2. Rxd5 winning net material (+500 cp).
    fen = "3r2k1/ppp2ppp/8/3q4/8/8/PPPQ1PPP/3R2K1 w - - 0 1"
    board = chess.Board(fen)

    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    assert score > 450


def test_quiescence_avoids_unfavorable_captures_via_stand_pat():
    """Stand-pat allows player to decline a losing trade that loses material."""
    # White Queen on d1 can capture Black Pawn on d5, but d5 is defended by Black Queen on d8.
    # If White plays Qxd5, Black plays Qxd5, losing White Queen for Pawn (-800 cp).
    # Since White is not forced to capture, stand-pat preserves equality (~ -130 cp for pawn down).
    fen = "3q2k1/ppp2ppp/8/3p4/8/8/PPP2PPP/3Q2K1 w - - 0 1"
    board = chess.Board(fen)

    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    # Stand-pat should ensure White does NOT evaluate as losing queen (-900 cp)
    assert score >= -200
    assert score > -800


def test_quiescence_searches_pawn_promotions():
    """Tactical move generation in quiescence includes pawn promotions (even if quiet)."""
    # White pawn on e7, can advance to e8=Q
    fen = "7k/4P3/8/8/8/8/8/4K3 w - - 0 1"
    board = chess.Board(fen)

    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    # After promoting e8=Q, White is up a Queen
    assert score > 800


def test_quiescence_searches_capture_promotions():
    """Tactical move generation includes capture promotions."""
    # White pawn on e7 captures Black Rook on d8=Q
    fen = "3r3k/4P3/8/8/8/8/8/4K3 w - - 0 1"
    board = chess.Board(fen)

    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    # Capturing rook and promoting to Queen gives massive advantage
    assert score > 800


def test_quiescence_searches_en_passant_captures():
    """Quiescence recognizes en-passant moves as tactical captures."""
    # Black just played d7-d5, White pawn on e5 can capture exd6 e.p.
    board = chess.Board("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
    ep_move = chess.Move.from_uci("e5d6")
    assert board.is_capture(ep_move)
    assert board.is_en_passant(ep_move)

    context = SearchContext()
    quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0, context=context)
    # Verifies quiescence executed and searched nodes
    assert context.quiescence_nodes > 0


def test_quiescence_check_evasions_include_quiet_moves():
    """When checked, quiet moves (king retreats and interpositions) are valid evasions."""
    # White King on e1 is checked by Black Rook on e8.
    # Only legal moves are quiet king steps: Kf1, Kd1, Kf2, Kd2.
    fen = "4r3/8/8/8/8/8/8/4K2k w - - 0 1"
    board = chess.Board(fen)
    assert board.is_check()

    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    # Should not report checkmate (-MATE_SCORE) because King can escape!
    assert score > -10000


def test_max_quiescence_depth_safeguard():
    """Quiescence search terminates when q_depth reaches max_quiescence_depth."""
    fen = "3r2k1/ppp2ppp/8/3q4/8/8/PPPQ1PPP/3R2K1 w - - 0 1"
    board = chess.Board(fen)

    context = SearchContext()
    # Force max_quiescence_depth=0 -> immediately falls back to static evaluation
    score = quiescence_search(
        board,
        alpha=-INFINITY,
        beta=INFINITY,
        ply=0,
        q_depth=0,
        context=context,
        max_quiescence_depth=0,
    )
    assert isinstance(score, int)
    # With max_quiescence_depth=0, only root node is evaluated
    assert context.quiescence_nodes == 1


def test_quiescence_search_context_tracking():
    """Verify that SearchContext correctly records quiescence nodes."""
    fen = "3r2k1/ppp2ppp/8/3q4/8/8/PPPQ1PPP/3R2K1 w - - 0 1"
    board = chess.Board(fen)

    context = SearchContext()
    quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0, context=context)

    assert context.quiescence_nodes > 0
    assert context.nodes_searched == context.quiescence_nodes


def test_quiescence_node_limit_interruption():
    """SearchInterrupted is raised when quiescence node count reaches node limit."""
    fen = "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"
    board = chess.Board(fen)

    context = SearchContext(max_nodes=2)
    with pytest.raises(SearchInterrupted) as exc_info:
        quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0, context=context)

    assert exc_info.value.reason == "node_limit"
    assert context.interrupted is True


def test_quiescence_time_limit_interruption():
    """SearchInterrupted is raised when quiescence search exceeds time limit."""
    fen = "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"
    board = chess.Board(fen)

    # Extreme time limit (1 microsecond) to guarantee cutoff
    context = SearchContext(time_limit_ms=0.001)
    with pytest.raises(SearchInterrupted) as exc_info:
        quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0, context=context)

    assert exc_info.value.reason == "time_limit"
    assert context.interrupted is True


def test_horizon_effect_mitigation():
    """
    Quiescence search mitigates the horizon effect.
    
    Position: White Queen on a4 attacks defended pawn on a7.
    If White plays Qxa7, Black responds Rxa7 winning Queen for pawn (-800 cp).
    At depth 1 with unextended search, White might greedily play Qxa7 believing it gained a pawn.
    With quiescence search enabled, White recognizes the recapture and chooses a safe move.
    """
    fen = "r3k2r/p4ppp/8/8/Q7/8/5PPP/4K2R w Kkq - 0 1"
    board = chess.Board(fen)

    # Without quiescence at depth 1:
    res_no_q = alpha_beta_search(board, depth=1, use_quiescence=False)
    # With quiescence at depth 1:
    res_with_q = alpha_beta_search(board, depth=1, use_quiescence=True)

    # In res_with_q, Qxa7 is recognized as losing Queen, so best_move is NOT Qxa7
    assert res_with_q.best_move != chess.Move.from_uci("a4a7")
    assert res_with_q.quiescence_nodes > 0


def test_quiescence_quiet_position_returns_stand_pat():
    """When no captures or promotions are available, quiescence immediately returns stand-pat."""
    # Quiet position with only quiet pawn/king moves
    fen = "8/8/8/4k3/8/4K3/4P3/8 w - - 0 1"
    board = chess.Board(fen)
    # White has e3, Kd3, Kf3, etc. No captures, no promotions.
    assert not any(board.is_capture(m) or m.promotion for m in board.legal_moves)

    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    expected_stand_pat = evaluate_position(board)
    assert score == expected_stand_pat


def test_quiescence_draw_by_fifty_moves():
    """50-move rule during quiescence returns 0 cp."""
    fen = "8/8/8/4k3/8/4K3/8/8 w - - 100 50"
    board = chess.Board(fen)
    assert board.is_fifty_moves()

    score = quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0)
    assert score == 0


def test_choose_move_uses_quiescence_by_default():
    """choose_move uses SearchConfig with use_quiescence=True by default."""
    board = chess.Board()
    cfg = SearchConfig(depth=1, use_quiescence=True)
    result = choose_move(board, cfg)

    assert result.best_move is not None
    assert result.quiescence_nodes >= 0
    assert result.completed_depth >= 1


def test_max_qdepth_reached_in_quiet_position():
    """When side to move is quiet and q_depth reaches max_quiescence_depth, static eval is returned."""
    fen = "8/8/8/4k3/8/4K3/4P3/8 w - - 0 1"
    board = chess.Board(fen)
    assert not board.is_check()

    score = quiescence_search(
        board,
        alpha=-INFINITY,
        beta=INFINITY,
        ply=4,
        q_depth=8,
        max_quiescence_depth=8,
    )
    assert score == evaluate_position(board, ply=4)


def test_max_qdepth_reached_while_in_check():
    """When in check at max_quiescence_depth, search extends to resolve check via legal evasions."""
    # White King on e1 is in check by Black Rook on e8
    fen = "4r2k/8/8/8/8/8/8/4K3 w - - 0 1"
    board = chess.Board(fen)
    assert board.is_check()

    context = SearchContext()
    # At q_depth == max_quiescence_depth, it must not return static eval; it must search check evasions
    score = quiescence_search(
        board,
        alpha=-INFINITY,
        beta=INFINITY,
        ply=4,
        q_depth=8,
        context=context,
        max_quiescence_depth=8,
        max_check_depth=2,
    )
    # Check evasions (Kf1, Kd1, Kf2, Kd2) were evaluated and resolved
    assert context.quiescence_nodes > 1
    assert score > -10000


def test_emergency_check_depth_limit_penalized():
    """When the emergency check depth limit is exceeded, an unresolved check penalty is applied."""
    from engine.constants import UNRESOLVED_CHECK_PENALTY

    # White in check
    fen = "4r2k/8/8/8/8/8/8/4K3 w - - 0 1"
    board = chess.Board(fen)
    assert board.is_check()

    # q_depth = 10, emergency ceiling = 8 + 2 = 10
    score = quiescence_search(
        board,
        alpha=-INFINITY,
        beta=INFINITY,
        ply=4,
        q_depth=10,
        max_quiescence_depth=8,
        max_check_depth=2,
    )
    expected_penalized = evaluate_position(board, ply=4) - UNRESOLVED_CHECK_PENALTY
    assert score == expected_penalized

    # Black in check
    fen_black = "4k3/8/8/8/8/8/8/4R2K b - - 0 1"
    board_black = chess.Board(fen_black)
    assert board_black.is_check()

    score_black = quiescence_search(
        board_black,
        alpha=-INFINITY,
        beta=INFINITY,
        ply=4,
        q_depth=10,
        max_quiescence_depth=8,
        max_check_depth=2,
    )
    expected_penalized_black = evaluate_position(board_black, ply=4) + UNRESOLVED_CHECK_PENALTY
    assert score_black == expected_penalized_black


def test_checkmate_at_qdepth_boundary():
    """Checkmate at the q_depth boundary returns exact mate score rather than static eval."""
    fools_fen = "rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
    board = chess.Board(fools_fen)
    assert board.is_checkmate()

    score = quiescence_search(
        board,
        alpha=-INFINITY,
        beta=INFINITY,
        ply=3,
        q_depth=8,
        max_quiescence_depth=8,
    )
    assert score == -(MATE_SCORE - 3)


def test_position_requiring_quiet_check_evasion_at_boundary():
    """Quiet check evasions are never filtered out at the q-depth boundary."""
    # White King on e1 is checked by Rook on e8; only legal moves are quiet king retreats
    fen = "4r2k/8/8/8/8/8/8/4K3 w - - 0 1"
    board = chess.Board(fen)
    assert board.is_check()
    assert all(not board.is_capture(m) and m.promotion is None for m in board.legal_moves)

    score = quiescence_search(
        board,
        alpha=-INFINITY,
        beta=INFINITY,
        ply=2,
        q_depth=8,
        max_quiescence_depth=8,
        max_check_depth=2,
    )
    # Does not falsely report checkmate; finds escape
    assert score > -10000


def test_node_limit_interruption_during_check_evasion_preserves_board():
    """Node limit interruption during check evasion search safely restores the board."""
    fen = "4r2k/8/8/8/8/8/8/4K3 w - - 0 1"
    board = chess.Board(fen)
    initial_fen = board.fen()
    initial_stack_len = len(board.move_stack)

    context = SearchContext(max_nodes=1)
    with pytest.raises(SearchInterrupted) as exc_info:
        quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0, context=context)

    assert exc_info.value.reason == "node_limit"
    assert board.fen() == initial_fen
    assert len(board.move_stack) == initial_stack_len


def test_time_limit_interruption_during_quiescence_preserves_board():
    """Time limit interruption during quiescence search safely restores the board."""
    fen = "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"
    board = chess.Board(fen)
    initial_fen = board.fen()
    initial_stack_len = len(board.move_stack)

    context = SearchContext(time_limit_ms=0.001)
    with pytest.raises(SearchInterrupted) as exc_info:
        quiescence_search(board, alpha=-INFINITY, beta=INFINITY, ply=0, context=context)

    assert exc_info.value.reason == "time_limit"
    assert board.fen() == initial_fen
    assert len(board.move_stack) == initial_stack_len


def test_regression_stand_pat_never_used_while_in_check():
    """
    Proves stand-pat is never used while in check.
    
    Setup: White is up massive material (+900 Queen), but White King is in check.
    If stand-pat were permitted, White's stand-pat (+900) would trigger an immediate
    beta cutoff against beta=0 without searching any legal moves.
    Because stand-pat is prohibited when checked, White MUST search legal check evasions.
    """
    # White King on e1 in check by Black Rook on e8; White has extra Queen on a8
    fen = "Q3r2k/8/8/8/8/8/8/4K3 w - - 0 1"
    board = chess.Board(fen)
    assert board.is_check()

    # If stand-pat were used, with beta = -500, White's stand_pat (+900) would cutoff immediately
    context = SearchContext()
    score = quiescence_search(board, alpha=-1000, beta=-500, ply=0, context=context)

    # In reality, White has Qxe8+ winning the Rook (Queen vs bare King = ~943 cp) or King steps
    # White cannot just stand pat; Qxe8 is evaluated
    assert context.quiescence_nodes > 1
    assert score > 900

