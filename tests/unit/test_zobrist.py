"""Unit tests for deterministic Zobrist hashing."""

import chess
import pytest

from engine.search.zobrist import (
    compute_zobrist_hash,
    update_zobrist_hash,
    verify_zobrist_hash,
    compute_castling_index,
    ZOBRIST_BLACK_TO_MOVE,
    ZOBRIST_SEED,
)


def test_zobrist_deterministic_and_reproducible():
    """Verify that Zobrist keys are completely deterministic across function invocations."""
    board1 = chess.Board()
    board2 = chess.Board()

    hash1 = compute_zobrist_hash(board1)
    hash2 = compute_zobrist_hash(board2)

    assert hash1 == hash2
    assert isinstance(hash1, int)
    assert 0 <= hash1 < (1 << 64)
    assert ZOBRIST_SEED == 0x20261031_57A6E7


def test_identical_positions_produce_identical_hashes():
    """Positions reached via different transposition move sequences produce identical Zobrist hashes."""
    # Sequence A: 1. d4 Nf6 2. c4
    board_a = chess.Board()
    board_a.push_san("d4")
    board_a.push_san("Nf6")
    board_a.push_san("c4")

    # Sequence B: 1. c4 Nf6 2. d4 (transposition)
    board_b = chess.Board()
    board_b.push_san("c4")
    board_b.push_san("Nf6")
    board_b.push_san("d4")

    assert board_a.fen() == board_b.fen()
    assert compute_zobrist_hash(board_a) == compute_zobrist_hash(board_b)


def test_different_side_to_move_produces_different_hashes():
    """Identical piece placement with different side to move produces different hashes."""
    # White to move
    fen_white = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    # Black to move (same pieces and rights)
    fen_black = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"

    board_white = chess.Board(fen_white)
    board_black = chess.Board(fen_black)

    hash_white = compute_zobrist_hash(board_white)
    hash_black = compute_zobrist_hash(board_black)

    assert hash_white != hash_black
    # Specifically differs by XOR of ZOBRIST_BLACK_TO_MOVE
    assert (hash_white ^ hash_black) == ZOBRIST_BLACK_TO_MOVE


def test_different_castling_rights_produce_different_hashes():
    """Different castling rights availability produces distinct hashes."""
    fen_all = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
    fen_no_white = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w kq - 0 1"
    fen_only_wk = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w Kkq - 0 1"

    hash_all = compute_zobrist_hash(chess.Board(fen_all))
    hash_no_white = compute_zobrist_hash(chess.Board(fen_no_white))
    hash_only_wk = compute_zobrist_hash(chess.Board(fen_only_wk))

    assert hash_all != hash_no_white
    assert hash_all != hash_only_wk
    assert hash_no_white != hash_only_wk


def test_different_piece_placements_produce_different_hashes():
    """Different piece arrangements produce unique hash values."""
    board_start = chess.Board()
    board_e4 = chess.Board()
    board_e4.push_san("e4")

    assert compute_zobrist_hash(board_start) != compute_zobrist_hash(board_e4)


def test_en_passant_relevant_vs_irrelevant():
    """
    En passant file is only included when an en passant capture is legally available.
    
    If an EP square exists but cannot be legally captured, the hash remains identical
    to a position without EP square (avoiding false transposition misses).
    """
    # 1. After 1. e4: ep_square is e3, but Black has NO pawns on d4 or f4 to capture e.p.
    b1 = chess.Board()
    b1.push_san("e4")
    assert b1.ep_square is not None
    assert not b1.has_legal_en_passant()

    # Create same position without ep_square flag
    b1_no_ep = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
    assert b1_no_ep.ep_square is None

    assert compute_zobrist_hash(b1) == compute_zobrist_hash(b1_no_ep)

    # 2. When en passant IS legally possible:
    b_legal_ep = chess.Board("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
    assert b_legal_ep.has_legal_en_passant()

    b_no_legal_ep = chess.Board("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")

    assert compute_zobrist_hash(b_legal_ep) != compute_zobrist_hash(b_no_legal_ep)


def test_incremental_hash_matches_full_recomputation_standard_moves():
    """Incremental hash updates match compute_zobrist_hash for standard opening moves."""
    board = chess.Board()
    h = compute_zobrist_hash(board)

    moves = ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6", "d2d3", "f8c5"]
    for uci in moves:
        m = chess.Move.from_uci(uci)
        b_prev = board.copy()
        board.push(m)
        h = update_zobrist_hash(h, b_prev, m, board)
        assert h == compute_zobrist_hash(board)
        assert verify_zobrist_hash(board, h)


def test_incremental_hash_matches_full_recomputation_captures():
    """Incremental hash updates match compute_zobrist_hash for piece captures."""
    board = chess.Board("r1bqk2r/pppp1ppp/2n2n2/4p3/1bB1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5")
    h = compute_zobrist_hash(board)

    # 1. d3 d5 2. exd5 Nxd5 3. Nxd5 Qxd5
    moves = ["d2d3", "d7d5", "e4d5", "f6d5", "c3d5", "d8d5"]
    for uci in moves:
        m = chess.Move.from_uci(uci)
        b_prev = board.copy()
        board.push(m)
        h = update_zobrist_hash(h, b_prev, m, board)
        assert h == compute_zobrist_hash(board)


def test_incremental_hash_matches_full_recomputation_castling():
    """Incremental hash updates match compute_zobrist_hash for kingside and queenside castling."""
    # Kingside castling
    b_kingside = chess.Board("r1bqk2r/pppp1ppp/2n2n2/4p3/1bB1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5")
    h_k = compute_zobrist_hash(b_kingside)
    m_k = chess.Move.from_uci("e1g1")
    b_k_prev = b_kingside.copy()
    b_kingside.push(m_k)
    h_k_inc = update_zobrist_hash(h_k, b_k_prev, m_k, b_kingside)
    assert h_k_inc == compute_zobrist_hash(b_kingside)

    # Queenside castling
    b_queenside = chess.Board("r3k2r/pppq1ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPPQ1PPP/R3K2R w KQkq - 4 8")
    h_q = compute_zobrist_hash(b_queenside)
    m_q = chess.Move.from_uci("e1c1")
    b_q_prev = b_queenside.copy()
    b_queenside.push(m_q)
    h_q_inc = update_zobrist_hash(h_q, b_q_prev, m_q, b_queenside)
    assert h_q_inc == compute_zobrist_hash(b_queenside)

    # Black Kingside castling
    b_bk = chess.Board("r1bqk2r/pppp1ppp/2n2n2/4p3/1bB1P3/2N2N2/PPPP1PPP/R1BQK2R b KQkq - 5 5")
    h_bk = compute_zobrist_hash(b_bk)
    m_bk = chess.Move.from_uci("e8g8")
    b_bk_prev = b_bk.copy()
    b_bk.push(m_bk)
    h_bk_inc = update_zobrist_hash(h_bk, b_bk_prev, m_bk, b_bk)
    assert h_bk_inc == compute_zobrist_hash(b_bk)

    # Black Queenside castling
    b_bq = chess.Board("r3k2r/pppq1ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPPQ1PPP/R3K2R b KQkq - 5 8")
    h_bq = compute_zobrist_hash(b_bq)
    m_bq = chess.Move.from_uci("e8c8")
    b_bq_prev = b_bq.copy()
    b_bq.push(m_bq)
    h_bq_inc = update_zobrist_hash(h_bq, b_bq_prev, m_bq, b_bq)
    assert h_bq_inc == compute_zobrist_hash(b_bq)


def test_incremental_hash_matches_full_recomputation_en_passant():
    """Incremental hash updates match compute_zobrist_hash for en-passant capture."""
    board = chess.Board("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
    h = compute_zobrist_hash(board)
    m = chess.Move.from_uci("e5d6")
    b_prev = board.copy()
    board.push(m)

    h_inc = update_zobrist_hash(h, b_prev, m, board)
    assert h_inc == compute_zobrist_hash(board)


def test_incremental_hash_matches_full_recomputation_promotion():
    """Incremental hash updates match compute_zobrist_hash for pawn promotions and capture promotions."""
    # Quiet promotion: e7-e8=Q
    board_promo = chess.Board("4k3/4P3/8/8/8/8/8/4K3 w - - 0 1")
    h_p = compute_zobrist_hash(board_promo)
    m_p = chess.Move.from_uci("e7e8q")
    b_p_prev = board_promo.copy()
    board_promo.push(m_p)
    h_p_inc = update_zobrist_hash(h_p, b_p_prev, m_p, board_promo)
    assert h_p_inc == compute_zobrist_hash(board_promo)

    # Capture promotion: e7xd8=N
    board_cap_promo = chess.Board("3r4/4P3/8/8/8/8/8/4K2k w - - 0 1")
    h_cp = compute_zobrist_hash(board_cap_promo)
    m_cp = chess.Move.from_uci("e7d8n")
    b_cp_prev = board_cap_promo.copy()
    board_cap_promo.push(m_cp)
    h_cp_inc = update_zobrist_hash(h_cp, b_cp_prev, m_cp, board_cap_promo)
    assert h_cp_inc == compute_zobrist_hash(board_cap_promo)


def test_zobrist_hash_restoration_after_make_unmake():
    """Position hash is identically restored after board.push() and board.pop()."""
    board = chess.Board("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5")
    initial_hash = compute_zobrist_hash(board)

    for move in board.legal_moves:
        board.push(move)
        assert compute_zobrist_hash(board) != initial_hash
        board.pop()
        assert compute_zobrist_hash(board) == initial_hash
