"""Unit tests for bounded Transposition Table with replacement policies and mate normalization."""

import chess
import pytest

from engine.constants import MATE_SCORE
from engine.search.transposition_table import Bound, TranspositionTable, TTEntry


def test_tt_store_and_retrieve_exact_cutoff():
    """Verify EXACT entry causes an immediate cutoff when depth is sufficient."""
    tt = TranspositionTable(size_mb=1)
    key = 0x1111_2222_3333_4444
    move = chess.Move.from_uci("e2e4")

    tt.store(key=key, depth=3, score=120, bound=Bound.EXACT, best_move=move, ply=0)

    # Probe at depth 3: cutoff triggers with exact score
    score, best_move, is_cutoff = tt.probe(key=key, depth=3, alpha=-500, beta=500, ply=0)

    assert is_cutoff is True
    assert score == 120
    assert best_move == move
    assert tt.hits == 1
    assert tt.cutoffs == 1


def test_tt_store_and_retrieve_lower_bound_cutoff():
    """Verify LOWER bound entry causes cutoff when score >= beta."""
    tt = TranspositionTable(size_mb=1)
    key = 0xAAAA_BBBB_CCCC_DDDD

    # Score is at least +200 cp
    tt.store(key=key, depth=3, score=200, bound=Bound.LOWER, ply=0)

    # Case A: beta is 150 (score 200 >= beta 150 -> cutoff!)
    score, _, is_cutoff = tt.probe(key=key, depth=3, alpha=-100, beta=150, ply=0)
    assert is_cutoff is True
    assert score == 200

    # Case B: beta is 250 (score 200 < beta 250 -> no cutoff)
    score, _, is_cutoff_no = tt.probe(key=key, depth=3, alpha=-100, beta=250, ply=0)
    assert is_cutoff_no is False


def test_tt_store_and_retrieve_upper_bound_cutoff():
    """Verify UPPER bound entry causes cutoff when score <= alpha."""
    tt = TranspositionTable(size_mb=1)
    key = 0x1234_5678_9ABC_DEF0

    # Score is at most -100 cp
    tt.store(key=key, depth=3, score=-100, bound=Bound.UPPER, ply=0)

    # Case A: alpha is -50 (score -100 <= alpha -50 -> cutoff!)
    score, _, is_cutoff = tt.probe(key=key, depth=3, alpha=-50, beta=500, ply=0)
    assert is_cutoff is True
    assert score == -100

    # Case B: alpha is -150 (score -100 > alpha -150 -> no cutoff)
    score, _, is_cutoff_no = tt.probe(key=key, depth=3, alpha=-150, beta=500, ply=0)
    assert is_cutoff_no is False


def test_tt_rejects_insufficient_depth_cutoffs():
    """A shallow entry cannot trigger a cutoff for a deeper search request."""
    tt = TranspositionTable(size_mb=1)
    key = 0x9999_8888_7777_6666
    move = chess.Move.from_uci("g1f3")

    # Stored at depth 2
    tt.store(key=key, depth=2, score=150, bound=Bound.EXACT, best_move=move, ply=0)

    # Probe requesting depth 4: no cutoff permitted, but best_move is returned for ordering
    score, best_move, is_cutoff = tt.probe(key=key, depth=4, alpha=-500, beta=500, ply=0)

    assert is_cutoff is False
    assert score == 150
    assert best_move == move  # Move ordering benefit retained


def test_tt_detects_key_mismatch_collisions():
    """Probing with a non-matching key returns a clean miss even if mapped to the same index."""
    tt = TranspositionTable(size_mb=1)

    # Construct two different keys that map to the exact same slot index
    key1 = 10
    key2 = 10 + tt.capacity
    assert (key1 & tt.mask) == (key2 & tt.mask)
    assert key1 != key2

    tt.store(key=key1, depth=3, score=100, bound=Bound.EXACT, ply=0)

    score, move, is_cutoff = tt.probe(key=key2, depth=3, alpha=-500, beta=500, ply=0)

    assert score is None
    assert move is None
    assert is_cutoff is False
    assert tt.hits == 0


def test_tt_replacement_prefers_deeper_entries():
    """Replacement policy preserves deeper existing entries over shallower collision entries."""
    tt = TranspositionTable(size_mb=1)
    idx = 42
    key_deep = (0x10000 & ~tt.mask) | idx
    key_shallow = (0x20000 & ~tt.mask) | idx

    # Store deep entry at generation 0
    tt.store(key=key_deep, depth=5, score=300, bound=Bound.EXACT, ply=0)
    assert tt.table[idx].depth == 5
    assert tt.table[idx].key == key_deep

    # Attempt to overwrite with shallow entry of same generation
    tt.store(key=key_shallow, depth=2, score=-50, bound=Bound.EXACT, ply=0)

    # Existing deep entry was protected
    assert tt.table[idx].key == key_deep
    assert tt.table[idx].depth == 5


def test_tt_replacement_overwrites_older_generations():
    """Replacement policy allows a new search entry to replace an entry from an older generation."""
    tt = TranspositionTable(size_mb=1)
    idx = 42
    key_old = (0x10000 & ~tt.mask) | idx
    key_new = (0x20000 & ~tt.mask) | idx

    # Generation 0
    tt.store(key=key_old, depth=5, score=300, bound=Bound.EXACT, ply=0)
    assert tt.table[idx].age == 0

    # Advance to Generation 1 (new search)
    tt.new_search()
    assert tt.generation == 1

    # Store entry in Generation 1: replaces older generation entry
    tt.store(key=key_new, depth=3, score=50, bound=Bound.EXACT, ply=0)

    assert tt.table[idx].key == key_new
    assert tt.table[idx].depth == 3
    assert tt.table[idx].age == 1


def test_tt_preserves_best_move_on_equal_depth_updates():
    """If an update doesn't have a best_move, it preserves the existing best_move."""
    tt = TranspositionTable(size_mb=1)
    key = 0x5555_6666_7777_8888
    move = chess.Move.from_uci("c2c4")

    # Store with best_move
    tt.store(key=key, depth=3, score=80, bound=Bound.LOWER, best_move=move, ply=0)

    # Update with EXACT bound and no best_move
    tt.store(key=key, depth=3, score=85, bound=Bound.EXACT, best_move=None, ply=0)

    entry = tt.table[key & tt.mask]
    assert entry.bound == Bound.EXACT
    assert entry.score == 85
    assert entry.best_move == move  # Move was preserved!


def test_mate_score_normalization_across_different_plies():
    """
    Mate scores normalized into the TT remain mathematically exact
    when retrieved at different search plies.
    """
    tt = TranspositionTable(size_mb=1)
    key_white_mates = 0x1111_0000_1111_0000

    # Position P has a forced mate in 2 plies from P.
    # When reached at search ply 1, the mate is at ply 3: raw score = MATE_SCORE - 3
    raw_score_ply1 = MATE_SCORE - 3
    tt.store(key=key_white_mates, depth=3, score=raw_score_ply1, bound=Bound.EXACT, ply=1)

    # In the TT, the stored normalized score must be root-independent: MATE_SCORE - 2
    entry = tt.table[key_white_mates & tt.mask]
    assert entry.score == MATE_SCORE - 2

    # Now, position P is reached via a different transposition path at search ply 4:
    # Since P mates in 2 plies, the total mate distance from root is 4 + 2 = 6 plies!
    # Expected denormalized score: MATE_SCORE - 6
    score_ply4, _, is_cutoff = tt.probe(
        key=key_white_mates, depth=3, alpha=-MATE_SCORE, beta=MATE_SCORE, ply=4
    )

    assert is_cutoff is True
    assert score_ply4 == MATE_SCORE - 6


def test_mate_score_normalization_black_delivers_mate():
    """Verify negative mate scores (Black delivering mate) normalize accurately."""
    tt = TranspositionTable(size_mb=1)
    key_black_mates = 0x2222_0000_2222_0000

    # Black delivers mate in 1 ply from position P.
    # Reached at ply 2: raw score = -(MATE_SCORE - 3)
    raw_score = -(MATE_SCORE - 3)
    tt.store(key=key_black_mates, depth=2, score=raw_score, bound=Bound.EXACT, ply=2)

    # Root independent normalized score: -(MATE_SCORE - 1)
    entry = tt.table[key_black_mates & tt.mask]
    assert entry.score == -(MATE_SCORE - 1)

    # Probed at ply 5: total distance from root = 5 + 1 = 6 plies -> -(MATE_SCORE - 6)
    retrieved_score, _, is_cutoff = tt.probe(
        key=key_black_mates, depth=2, alpha=-MATE_SCORE, beta=MATE_SCORE, ply=5
    )
    assert is_cutoff is True
    assert retrieved_score == -(MATE_SCORE - 6)


def test_tt_fifty_move_safety():
    """When fifty-move counts differ significantly near 100, score cutoff is suppressed."""
    tt = TranspositionTable(size_mb=1)
    key = 0x7777_7777_7777_7777

    # Stored with halfmove_clock = 95
    tt.store(key=key, depth=3, score=250, bound=Bound.EXACT, ply=0, halfmove_clock=95)

    # Probed with halfmove_clock = 10 (far from 50-move draw)
    # Cutoff must be suppressed because the 50-move contexts diverge!
    score, best_move, is_cutoff = tt.probe(
        key=key, depth=3, alpha=-500, beta=500, ply=0, halfmove_clock=10
    )

    assert is_cutoff is False


def test_tt_clear():
    """Verify clear() resets all slots, statistics, and generations."""
    tt = TranspositionTable(size_mb=1)
    tt.store(key=0x1234, depth=2, score=50, bound=Bound.EXACT, ply=0)
    tt.probe(key=0x1234, depth=2, alpha=-100, beta=100, ply=0)
    tt.new_search()

    assert tt.occupancy == 1
    assert tt.probes == 1
    assert tt.generation == 1

    tt.clear()

    assert tt.occupancy == 0
    assert tt.probes == 0
    assert tt.hits == 0
    assert tt.generation == 0
    assert all(entry is None for entry in tt.table)


def test_tt_statistics_properties():
    """Verify hit_rate, cutoff_rate, and occupancy_rate percentage calculations."""
    tt = TranspositionTable(size_mb=1)
    assert tt.hit_rate == 0.0
    assert tt.cutoff_rate == 0.0
    assert tt.occupancy_rate == 0.0

    key = 0x1234
    tt.store(key=key, depth=3, score=100, bound=Bound.EXACT, ply=0)
    tt.probe(key=key, depth=3, alpha=-500, beta=500, ply=0)

    assert tt.probes == 1
    assert tt.hits == 1
    assert tt.cutoffs == 1
    assert tt.hit_rate == 100.0
    assert tt.cutoff_rate == 100.0
    assert tt.occupancy_rate > 0.0


def test_tt_minimum_size_mb():
    """TranspositionTable clamps size_mb to minimum of 1."""
    tt_min = TranspositionTable(size_mb=0)
    assert tt_min.size_mb == 1
    assert tt_min.capacity >= 1024


def test_alpha_beta_tt_enabled_vs_disabled_correctness():
    """Alpha-Beta with TT produces identical legal moves and consistent scores to TT-disabled."""
    from engine.search.alpha_beta import alpha_beta_search

    fens = [
        chess.STARTING_FEN,
        "r1bqk2r/pppp1ppp/2n2n2/4p3/1bB1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5",
        "8/5pk1/4p1p1/8/1p6/1P4P1/5PKP/8 w - - 0 1",
    ]

    for fen in fens:
        board = chess.Board(fen)
        res_no_tt = alpha_beta_search(board, depth=3, use_transposition_table=False)
        res_with_tt = alpha_beta_search(board, depth=3, use_transposition_table=True)

        assert res_with_tt.best_move is not None
        assert res_with_tt.best_move in list(board.legal_moves)
        assert res_with_tt.score_cp == res_no_tt.score_cp
        assert res_with_tt.tt_stores > 0


def test_tt_node_reduction_on_repeated_search():
    """Searching a position with an already populated TT results in instant TT hits and cutoffs."""
    from engine.search.alpha_beta import alpha_beta_search
    from engine.search.ordering import SearchContext

    board = chess.Board("r1bqk2r/pppp1ppp/2n2n2/4p3/1bB1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5")
    tt = TranspositionTable(size_mb=2)
    ctx1 = SearchContext()
    ctx1.transposition_table = tt

    res1 = alpha_beta_search(board, depth=3, context=ctx1, use_transposition_table=True)

    # Search again using the same populated TT
    ctx2 = SearchContext()
    ctx2.transposition_table = tt
    res2 = alpha_beta_search(board, depth=3, context=ctx2, use_transposition_table=True)

    assert res2.best_move == res1.best_move
    assert res2.score_cp == res1.score_cp
    assert ctx2.tt_hits > 0
    assert ctx2.tt_cutoffs > 0
    # Second search should require far fewer nodes due to root/branch cutoffs
    assert ctx2.nodes_searched < ctx1.nodes_searched


def test_tt_checkmate_detection_unaffected():
    """Mate-in-1 is accurately found with TT enabled."""
    from engine.search.alpha_beta import alpha_beta_search

    fen_mate1 = "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B5/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4"
    board = chess.Board(fen_mate1)

    res = alpha_beta_search(board, depth=2, use_transposition_table=True)
    assert res.best_move == chess.Move.from_uci("h5f7")
    assert res.score_cp == MATE_SCORE - 1
    assert res.is_checkmate is True


def test_tt_board_restoration_guarantee():
    """Board state (FEN and move stack) is 100% preserved after search with TT enabled."""
    from engine.search.alpha_beta import alpha_beta_search

    fen = "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"
    board = chess.Board(fen)
    initial_fen = board.fen()
    initial_stack_len = len(board.move_stack)

    res = alpha_beta_search(board, depth=3, use_transposition_table=True)

    assert board.fen() == initial_fen
    assert len(board.move_stack) == initial_stack_len


def test_tt_fifty_move_safety_asymmetric_horizons():
    """
    Fifty-move safety accounts for both stored and current halfmove clocks
    and their respective search horizons.
    """
    tt = TranspositionTable(size_mb=1)
    key = 0x8888_8888_8888_8888
    move = chess.Move.from_uci("e2e4")

    # Scenario A: Stored H=0, D=5; Current H=90, D=5 (Prompt example)
    # Stored horizon is far from 50-move draw, but current search is near threshold (H >= 90).
    tt.store(key=key, depth=5, score=300, bound=Bound.EXACT, best_move=move, halfmove_clock=0)
    score, best_move, is_cutoff = tt.probe(key=key, depth=5, alpha=-500, beta=500, ply=0, halfmove_clock=90)
    assert is_cutoff is False
    assert best_move == move  # Move ordering preserved!

    # Scenario B: Stored H=0, D=5; Current H=96, D=5
    # Current search horizon 96 + 5 = 101 >= 100 can cross fifty-move draw.
    tt.clear()
    tt.store(key=key, depth=5, score=300, bound=Bound.EXACT, best_move=move, halfmove_clock=0)
    score, best_move, is_cutoff = tt.probe(key=key, depth=5, alpha=-500, beta=500, ply=0, halfmove_clock=96)
    assert is_cutoff is False
    assert best_move == move

    # Scenario C: Stored H=85, D=16; Current H=0, D=5
    # Stored search horizon 85 + 16 = 101 >= 100 may have been influenced by 50-move draw.
    tt.clear()
    tt.store(key=key, depth=16, score=0, bound=Bound.EXACT, best_move=move, halfmove_clock=85)
    score, best_move, is_cutoff = tt.probe(key=key, depth=5, alpha=-500, beta=500, ply=0, halfmove_clock=0)
    assert is_cutoff is False
    assert best_move == move

    # Scenario D: Safe score reuse when both clocks are well below threshold
    # Stored H=10, D=4; Current H=14, D=4. Neither can approach 100 plies.
    tt.clear()
    tt.store(key=key, depth=4, score=150, bound=Bound.EXACT, best_move=move, halfmove_clock=10)
    score, best_move, is_cutoff = tt.probe(key=key, depth=4, alpha=-500, beta=500, ply=0, halfmove_clock=14)
    assert is_cutoff is True
    assert score == 150
    assert best_move == move

    # Scenario E: Clocks match exactly (H_stored == H_current)
    # Even near threshold, matching clocks ensure identical draw distance.
    tt.clear()
    tt.store(key=key, depth=3, score=250, bound=Bound.EXACT, best_move=move, halfmove_clock=95)
    score, best_move, is_cutoff = tt.probe(key=key, depth=3, alpha=-500, beta=500, ply=0, halfmove_clock=95)
    assert is_cutoff is True
    assert score == 250
    assert best_move == move


def test_tt_store_move_only_preserves_ordering_without_cutoff():
    """store_move_only provides safe move ordering without triggering false score cutoffs."""
    tt = TranspositionTable(size_mb=1)
    key = 0x9999_9999_9999_9999
    suggested = chess.Move.from_uci("g1f3")

    tt.store_move_only(key=key, best_move=suggested)

    # Probing at depth 3 must NOT cutoff, but MUST return the suggested move
    score, best_move, is_cutoff = tt.probe(key=key, depth=3, alpha=-1000, beta=1000, ply=0)
    assert is_cutoff is False
    assert best_move == suggested

    # Updating an existing valid score with store_move_only must preserve existing score/depth
    tt.store(key=key, depth=4, score=75, bound=Bound.EXACT, best_move=None, ply=0)
    new_move = chess.Move.from_uci("e2e4")
    tt.store_move_only(key=key, best_move=new_move)

    score2, best_move2, is_cutoff2 = tt.probe(key=key, depth=4, alpha=-1000, beta=1000, ply=0)
    assert is_cutoff2 is True
    assert score2 == 75
    assert best_move2 == new_move


def test_tt_repetition_ancestor_contamination_prevented():
    """
    A repetition draw in a subtree must not contaminate ancestor nodes with reusable exact scores.
    """
    from engine.search.alpha_beta import alpha_beta_search
    from engine.search.ordering import SearchContext

    # Setup a position where moves leading to repetition exist
    board = chess.Board()
    # Play moves to establish a game history: 1. Nf3 Nf6 2. Ng1 Ng8 (position repeated once)
    board.push_san("Nf3")
    board.push_san("Nf6")
    board.push_san("Ng1")
    board.push_san("Ng8")
    assert board.is_repetition(2)

    # Search with TT enabled
    tt = TranspositionTable(size_mb=2)
    ctx = SearchContext()
    ctx.transposition_table = tt

    res = alpha_beta_search(board, depth=3, context=ctx, use_transposition_table=True)
    assert res.best_move is not None

    # Now create a fresh board in the starting position with NO move history
    fresh_board = chess.Board()
    fresh_ctx = SearchContext()
    fresh_ctx.transposition_table = tt  # Reusing the TT

    fresh_res = alpha_beta_search(fresh_board, depth=3, context=fresh_ctx, use_transposition_table=True)
    # The fresh board without repetition history must NOT be forced into a draw by cached repetition scores
    expected_fresh = alpha_beta_search(fresh_board.copy(), depth=3, use_transposition_table=False)
    assert fresh_res.best_move == expected_fresh.best_move
    assert fresh_res.score_cp == expected_fresh.score_cp
    assert fresh_res.score_cp > 0  # White has normal opening advantage, not a false draw!


def test_tt_different_repetition_histories_match_disabled():
    """
    Identical board positions reached via different repetition histories
    produce exact score and move agreement between TT-enabled and TT-disabled searches.
    """
    from engine.search.alpha_beta import alpha_beta_search

    # Position reached via 1. e4 e5 2. Nf3 Nc6 3. Ng1 Nb8 4. Nf3 Nc6 (repetition history)
    b1 = chess.Board()
    for san in ["e4", "e5", "Nf3", "Nc6", "Ng1", "Nb8", "Nf3", "Nc6"]:
        b1.push_san(san)

    # Identical piece placement reached without repetition: 1. e4 e5 2. Nf3 Nc6
    b2 = chess.Board()
    for san in ["e4", "e5", "Nf3", "Nc6"]:
        b2.push_san(san)

    assert b1.fen().split()[0] == b2.fen().split()[0]

    # Search b1 with TT disabled vs enabled
    res1_nott = alpha_beta_search(b1.copy(), depth=3, use_transposition_table=False, use_quiescence=True)
    res1_tt = alpha_beta_search(b1.copy(), depth=3, use_transposition_table=True, use_quiescence=True)

    assert res1_tt.best_move == res1_nott.best_move
    assert res1_tt.score_cp == res1_nott.score_cp

    # Search b2 with TT disabled vs enabled
    res2_nott = alpha_beta_search(b2.copy(), depth=3, use_transposition_table=False, use_quiescence=True)
    res2_tt = alpha_beta_search(b2.copy(), depth=3, use_transposition_table=True, use_quiescence=True)

    assert res2_tt.best_move == res2_nott.best_move
    assert res2_tt.score_cp == res2_nott.score_cp


def test_tt_node_semantics_identity():
    """
    Search telemetry verifies the invariant: nodes_searched == normal_nodes + quiescence_nodes.
    """
    from engine.search.alpha_beta import alpha_beta_search

    board = chess.Board("r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5")
    res = alpha_beta_search(board, depth=3, use_transposition_table=True, use_quiescence=True)

    assert res.nodes_searched > 0
    assert res.quiescence_nodes > 0
    normal_nodes = res.nodes_searched - res.quiescence_nodes
    assert normal_nodes > 0
    assert res.nodes_searched == normal_nodes + res.quiescence_nodes


def test_tt_fifty_move_safety_with_quiescence_extension():
    """
    Fifty-move safety accounts for potential quiescence check-evasion extensions
    beyond nominal search depth.
    """
    tt = TranspositionTable(size_mb=1)
    key = 0xAAAA_BBBB_CCCC_DDDD
    move = chess.Move.from_uci("e2e4")

    # Stored with H=0, D=3
    tt.store(key=key, depth=3, score=200, bound=Bound.EXACT, best_move=move, halfmove_clock=0)

    # Probed with H=87, D=3.
    # Note: 87 < 90, and nominal horizon 87 + 3 = 90 < 100.
    # BUT with default max_extension = 10 (8 q_depth + 2 check_depth):
    # 87 + 3 + 10 = 100 >= 100!
    # A quiet check evasion in quiescence could reach 100 halfmoves!
    # Therefore, cutoff MUST be suppressed, but best_move preserved for move ordering.
    score, best_move, is_cutoff = tt.probe(
        key=key, depth=3, alpha=-500, beta=500, ply=0, halfmove_clock=87, max_extension=10
    )
    assert is_cutoff is False
    assert best_move == move

    # In contrast, when H=80, D=3:
    # 80 + 3 + 10 = 93 < 100 and 80 < 90. Neither can reach 50-move draw.
    score_safe, best_move_safe, is_cutoff_safe = tt.probe(
        key=key, depth=3, alpha=-500, beta=500, ply=0, halfmove_clock=80, max_extension=10
    )
    assert is_cutoff_safe is True
    assert score_safe == 200
    assert best_move_safe == move


def test_quiescence_repetition_draw_propagates_path_dependence():
    """
    When a repetition draw occurs within quiescence search, path-dependence is
    propagated and the caller does not store reusable score bounds in the TT.
    """
    from engine.search.quiescence import quiescence_search
    from engine.search.alpha_beta import alpha_beta_search
    from engine.search.ordering import SearchContext
    from engine.search.zobrist import compute_zobrist_hash

    # Construct a board where a repeating sequence can be played
    board = chess.Board()
    for san in ["Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6"]:
        board.push_san(san)

    # Position is already repeated twice: playing Ng1 Ng8 will hit 3-fold repetition
    assert board.is_repetition(2)

    # Test quiescence_search directly with return_path_dep=True
    score, is_pd = quiescence_search(board.copy(), alpha=-1000, beta=1000, ply=0, return_path_dep=True)
    assert is_pd is True

    # Test that full alpha_beta search does not store a reusable score bound in TT
    tt = TranspositionTable(size_mb=1)
    ctx = SearchContext()
    ctx.transposition_table = tt

    res = alpha_beta_search(board, depth=1, context=ctx, use_transposition_table=True, use_quiescence=True)
    assert res.best_move is not None

    # Probe the root key: because root was path-dependent, no EXACT score was stored
    root_key = compute_zobrist_hash(board)
    tt_score, _, is_cutoff = tt.probe(key=root_key, depth=1, alpha=-1000, beta=1000, ply=0)
    assert is_cutoff is False


def test_quiescence_fifty_move_draw_propagates_path_dependence():
    """
    When fifty-move draw is reached during quiescence check evasion,
    path-dependence is correctly propagated to prevent contaminating the TT.
    """
    from engine.search.quiescence import quiescence_search
    from engine.search.ordering import SearchContext
    from engine.search.alpha_beta import alpha_beta_search

    # White king on h1 in check from black rook on a1; black king on h8
    # White has one legal evasion: Kh1-g2 (quiet king move, no pawn move, no capture)
    board = chess.Board("7k/8/8/8/8/8/8/r6K w - - 99 50")
    assert board.is_check()
    assert board.halfmove_clock == 99

    # Quiescence search explores Kh1-g2: halfmove_clock becomes 100 -> is_fifty_moves() triggers draw (0 cp)
    ctx = SearchContext()
    score, is_pd = quiescence_search(board.copy(), alpha=-1000, beta=1000, ply=0, context=ctx, return_path_dep=True)
    assert score == 0  # Draw
    assert is_pd is True  # Flagged as path-dependent!


def test_tt_divergent_halfmove_clocks_no_false_draw_contamination():
    """
    Search on position with H=98 (hits 50-move draw) does not contaminate
    subsequent search on identical piece layout with H=10.
    """
    from engine.search.alpha_beta import alpha_beta_search
    from engine.search.ordering import SearchContext

    # Position A: Queen vs bare King near 50-move threshold (H=98)
    # 4k3/8/8/8/8/8/8/4KQ2 w - - 98 50
    board_draw = chess.Board("4k3/8/8/8/8/8/8/4KQ2 w - - 98 50")

    tt = TranspositionTable(size_mb=2)
    ctx1 = SearchContext()
    ctx1.transposition_table = tt

    # Search at depth 3: in 2 plies without pawn move/capture, H hits 100 (draw)
    res_draw = alpha_beta_search(board_draw, depth=3, context=ctx1, use_transposition_table=True, use_quiescence=True)

    # Now create Position B: exact same piece layout, but H=10 (nowhere near draw)
    board_win = chess.Board("4k3/8/8/8/8/8/8/4KQ2 w - - 10 50")
    ctx2 = SearchContext()
    ctx2.transposition_table = tt  # Reusing TT

    res_win = alpha_beta_search(board_win, depth=3, context=ctx2, use_transposition_table=True, use_quiescence=True)

    # Position B must NOT be contaminated by Position A's draw score!
    # White with queen vs bare king must have a winning score (> 500 cp)
    assert res_win.score_cp > 500
    assert res_win.is_draw is False


def test_tt_extract_pv():
    """Verify TT extract_pv correctly follows chain of best moves and avoids illegal cycles."""
    from engine.search.zobrist import compute_zobrist_hash

    board = chess.Board()
    tt = TranspositionTable(size_mb=1)

    # Empty TT returns empty PV
    pv_uci, pv_san = tt.extract_pv(board)
    assert pv_uci == []
    assert pv_san == []

    # Store a best move for root position
    root_key = compute_zobrist_hash(board)
    m1 = chess.Move.from_uci("e2e4")
    tt.store(key=root_key, depth=3, score=25, bound=Bound.EXACT, ply=0, best_move=m1)

    # Push m1 and store best move for child
    b2 = board.copy()
    b2.push(m1)
    k2 = compute_zobrist_hash(b2)
    m2 = chess.Move.from_uci("e7e5")
    tt.store(key=k2, depth=2, score=-20, bound=Bound.EXACT, ply=1, best_move=m2)

    # Extract PV
    pv_uci, pv_san = tt.extract_pv(board, max_length=5)
    assert pv_uci == ["e2e4", "e7e5"]
    assert pv_san == ["e4", "e5"]


def test_tt_extract_pv_with_authoritative_first_move():
    """Verify first_move parameter overrides root TT lookup and guarantees correct root move."""
    from engine.search.zobrist import compute_zobrist_hash

    board = chess.Board()
    tt = TranspositionTable(size_mb=1)

    # Incomplete iteration might have stored 'd2d4' at root
    root_key = compute_zobrist_hash(board)
    m_incomplete = chess.Move.from_uci("d2d4")
    tt.store(key=root_key, depth=3, score=10, bound=Bound.EXACT, ply=0, best_move=m_incomplete)

    # But completed iteration determined best move was 'e2e4'
    m_completed = chess.Move.from_uci("e2e4")
    b_after_e4 = board.copy()
    b_after_e4.push(m_completed)
    k_e4 = compute_zobrist_hash(b_after_e4)
    m_reply = chess.Move.from_uci("e7e5")
    tt.store(key=k_e4, depth=2, score=-10, bound=Bound.EXACT, ply=1, best_move=m_reply)

    pv_uci, pv_san = tt.extract_pv(board, max_length=5, first_move=m_completed)
    assert pv_uci == ["e2e4", "e7e5"]
    assert pv_san == ["e4", "e5"]


def test_tt_extract_pv_cycle_termination():
    """Verify repetitive cycle in TT does not result in infinite loop."""
    from engine.search.zobrist import compute_zobrist_hash

    board = chess.Board()
    tt = TranspositionTable(size_mb=1)

    # Move 1: Nf3
    m1 = chess.Move.from_uci("g1f3")
    tt.store(key=compute_zobrist_hash(board), depth=2, score=0, bound=Bound.EXACT, ply=0, best_move=m1)

    # Move 2: Nf6
    b1 = board.copy()
    b1.push(m1)
    m2 = chess.Move.from_uci("g8f6")
    tt.store(key=compute_zobrist_hash(b1), depth=2, score=0, bound=Bound.EXACT, ply=1, best_move=m2)

    # Move 3: Ng1 (cycle back)
    b2 = b1.copy()
    b2.push(m2)
    m3 = chess.Move.from_uci("f3g1")
    tt.store(key=compute_zobrist_hash(b2), depth=2, score=0, bound=Bound.EXACT, ply=2, best_move=m3)

    # Move 4: Ng8 (cycle back to root position)
    b3 = b2.copy()
    b3.push(m3)
    m4 = chess.Move.from_uci("f6g8")
    tt.store(key=compute_zobrist_hash(b3), depth=2, score=0, bound=Bound.EXACT, ply=3, best_move=m4)

    # Extraction must safely detect cycle and terminate
    pv_uci, pv_san = tt.extract_pv(board, max_length=10)
    assert len(pv_uci) <= 4
    assert pv_uci == ["g1f3", "g8f6", "f3g1", "f6g8"]






