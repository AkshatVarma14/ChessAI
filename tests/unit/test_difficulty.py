"""Unit tests for engine difficulty profiles and configuration."""

import pytest
from engine.difficulty import (
    DEFAULT_DIFFICULTY,
    DIFFICULTY_PROFILES,
    DifficultyLevel,
    DifficultyProfile,
    get_difficulty_profile,
    validate_difficulty,
)


class TestDifficultyProfiles:
    """Validates authoritative difficulty definitions and configuration bounds."""

    def test_all_five_difficulty_levels_exist(self) -> None:
        """Confirms that all 5 named difficulty levels exist in enum and registry."""
        expected_levels = {"beginner", "easy", "medium", "hard", "expert"}
        actual_enum_levels = {lvl.value for lvl in DifficultyLevel}
        actual_profile_levels = {lvl.value for lvl in DIFFICULTY_PROFILES.keys()}

        assert actual_enum_levels == expected_levels
        assert actual_profile_levels == expected_levels

    def test_default_difficulty_is_medium(self) -> None:
        """Verifies default difficulty preset is medium."""
        assert DEFAULT_DIFFICULTY == DifficultyLevel.MEDIUM
        assert get_difficulty_profile().level == DifficultyLevel.MEDIUM

    def test_profiles_have_logically_ordered_search_budgets(self) -> None:
        """
        Verifies that search depth, max nodes, and base time budgets scale monotonically
        from Beginner through Expert.
        """
        ordered_levels = [
            DifficultyLevel.BEGINNER,
            DifficultyLevel.EASY,
            DifficultyLevel.MEDIUM,
            DifficultyLevel.HARD,
            DifficultyLevel.EXPERT,
        ]

        depths = [DIFFICULTY_PROFILES[lvl].search_config.depth for lvl in ordered_levels]
        max_nodes = [DIFFICULTY_PROFILES[lvl].search_config.max_nodes for lvl in ordered_levels]
        base_times = [DIFFICULTY_PROFILES[lvl].base_time_ms for lvl in ordered_levels]
        max_times = [DIFFICULTY_PROFILES[lvl].max_time_ms for lvl in ordered_levels]

        # Depths strictly increase (1, 2, 3, 4, 5)
        for i in range(len(depths) - 1):
            assert depths[i] < depths[i + 1], f"Depth not monotonic at index {i}: {depths}"

        # Max nodes strictly increase
        for i in range(len(max_nodes) - 1):
            assert max_nodes[i] < max_nodes[i + 1], f"Max nodes not monotonic at index {i}: {max_nodes}"

        # Time budgets strictly increase
        for i in range(len(base_times) - 1):
            assert base_times[i] < base_times[i + 1], f"Base times not monotonic at index {i}: {base_times}"
            assert max_times[i] < max_times[i + 1], f"Max times not monotonic at index {i}: {max_times}"

    def test_quiescence_and_tt_settings_scale_with_difficulty(self) -> None:
        """Verifies quiescence search and TT sizing grow with difficulty."""
        beginner = DIFFICULTY_PROFILES[DifficultyLevel.BEGINNER].search_config
        easy = DIFFICULTY_PROFILES[DifficultyLevel.EASY].search_config
        medium = DIFFICULTY_PROFILES[DifficultyLevel.MEDIUM].search_config
        hard = DIFFICULTY_PROFILES[DifficultyLevel.HARD].search_config
        expert = DIFFICULTY_PROFILES[DifficultyLevel.EXPERT].search_config

        # Beginner has 0 quiet quiescence depth, safe check depth 1, and no TT
        assert beginner.use_quiescence is True
        assert beginner.max_quiescence_depth == 0
        assert beginner.max_check_depth == 1
        assert beginner.use_transposition_table is False

        # Easy through Expert have progressively deeper quiescence
        assert easy.use_quiescence is True
        assert medium.use_quiescence is True
        assert hard.use_quiescence is True
        assert expert.use_quiescence is True

        assert beginner.max_quiescence_depth < easy.max_quiescence_depth
        assert easy.max_quiescence_depth < medium.max_quiescence_depth
        assert medium.max_quiescence_depth < hard.max_quiescence_depth
        assert hard.max_quiescence_depth <= expert.max_quiescence_depth

        # TT size grows appropriately
        assert easy.transposition_table_size_mb <= medium.transposition_table_size_mb
        assert medium.transposition_table_size_mb < hard.transposition_table_size_mb
        assert hard.transposition_table_size_mb < expert.transposition_table_size_mb

    def test_get_difficulty_profile_case_insensitive(self) -> None:
        """Ensures string lookups handle whitespace and case correctly."""
        assert get_difficulty_profile("BEGINNER").level == DifficultyLevel.BEGINNER
        assert get_difficulty_profile("  Easy  ").level == DifficultyLevel.EASY
        assert get_difficulty_profile("Medium").level == DifficultyLevel.MEDIUM
        assert get_difficulty_profile("hArD").level == DifficultyLevel.HARD
        assert get_difficulty_profile("EXPERT").level == DifficultyLevel.EXPERT

    def test_invalid_difficulty_name_raises_value_error(self) -> None:
        """Ensures invalid difficulty names raise ValueError with clear guidance."""
        with pytest.raises(ValueError, match="Invalid difficulty 'super_grandmaster'"):
            get_difficulty_profile("super_grandmaster")

        with pytest.raises(ValueError, match="Difficulty must be a string or DifficultyLevel"):
            get_difficulty_profile(123)  # type: ignore[arg-type]

    def test_validate_difficulty_normalizes(self) -> None:
        """Verifies canonical string normalization."""
        assert validate_difficulty("  HARD  ") == "hard"
        assert validate_difficulty("Beginner") == "beginner"

    def test_profile_immutability(self) -> None:
        """Verifies DifficultyProfile instances are frozen and cannot be mutated."""
        profile = DIFFICULTY_PROFILES[DifficultyLevel.MEDIUM]
        with pytest.raises(AttributeError):
            profile.base_time_ms = 9999.0  # type: ignore[misc]

    def test_invalid_profile_time_bounds_validation(self) -> None:
        """Verifies DifficultyProfile dataclass post-init rejects invalid time bounds."""
        cfg = DIFFICULTY_PROFILES[DifficultyLevel.MEDIUM].search_config

        # min_time <= 0
        with pytest.raises(ValueError, match="min_time_ms must be positive"):
            DifficultyProfile(
                level=DifficultyLevel.MEDIUM,
                display_name="Test",
                description="Test",
                search_config=cfg,
                base_time_ms=500.0,
                max_time_ms=1000.0,
                min_time_ms=-10.0,
            )

        # base_time < min_time
        with pytest.raises(ValueError, match="base_time_ms .* cannot be less than min_time_ms"):
            DifficultyProfile(
                level=DifficultyLevel.MEDIUM,
                display_name="Test",
                description="Test",
                search_config=cfg,
                base_time_ms=50.0,
                max_time_ms=1000.0,
                min_time_ms=100.0,
            )

        # max_time < base_time
        with pytest.raises(ValueError, match="max_time_ms .* cannot be less than base_time_ms"):
            DifficultyProfile(
                level=DifficultyLevel.MEDIUM,
                display_name="Test",
                description="Test",
                search_config=cfg,
                base_time_ms=800.0,
                max_time_ms=400.0,
                min_time_ms=100.0,
            )


class TestBeginnerCheckEvasionAudit:
    """Targeted audit tests for Beginner difficulty and horizon check-evasion correctness."""

    def test_beginner_search_config_invariants(self) -> None:
        """
        Confirms Beginner difficulty profile has quiescence search enabled
        with max_quiescence_depth=0 and max_check_depth=1 per Stage 8.1 specification.
        """
        profile = get_difficulty_profile(DifficultyLevel.BEGINNER)
        cfg = profile.search_config
        assert cfg.depth == 1
        assert cfg.use_quiescence is True
        assert cfg.max_quiescence_depth == 0
        assert cfg.max_check_depth == 1
        assert cfg.use_move_ordering is False
        assert cfg.use_transposition_table is False

    def test_beginner_quiescence_activates_on_check_evasion_only(self) -> None:
        """
        Verifies that Beginner quiescent search explores check evasions
        when the horizon position is in check, but does NOT explore captures in quiet positions.
        """
        import chess
        from engine import choose_move

        # Quiet starting position: 20 legal root moves enter quiescence at q_depth=0,
        # but because max_quiescence_depth=0 and position is quiet, none expand into deeper q-nodes.
        start_board = chess.Board()
        start_res = choose_move(start_board, difficulty="beginner")
        num_start_moves = len(list(start_board.legal_moves))
        assert start_res.quiescence_nodes == num_start_moves, (
            f"Quiet position must evaluate exactly {num_start_moves} stand-pat q_depth=0 nodes without deep branching"
        )

        # Tactical position where White moves can deliver check:
        # e.g., Queen gives Qxf7+ -> Black is in check, which expands into q_depth=1 to evaluate evasions.
        tactical_board = chess.Board("rnbqkbnr/pppp1ppp/8/8/8/5Q2/PPPPP1PP/RNB1KBNR w KQkq - 0 1")
        tactical_res = choose_move(tactical_board, difficulty="beginner")
        num_tactical_moves = len(list(tactical_board.legal_moves))
        assert tactical_res.quiescence_nodes > num_tactical_moves, (
            f"Positions delivering check must expand beyond root q_depth=0 (got {tactical_res.quiescence_nodes} > {num_tactical_moves})"
        )
        assert tactical_res.best_move_san != "Qxf7+", "Must not blunder queen into defended square"

    def test_checked_positions_recognized_at_search_horizon(self) -> None:
        """
        Verifies that when nominal search reaches depth 0 while in check with use_quiescence=True,
        the check is recognized and not treated as a quiet static evaluation.
        """
        import chess
        from engine import choose_move
        from engine.search.alpha_beta import alpha_beta_search

        # Position where White queen can deliver Qxf7+ (losing Queen for pawn),
        # but Black king defends f7 (Kxf7).
        board = chess.Board("rnbqkbnr/pppp1ppp/8/8/8/5Q2/PPPPP1PP/RNB1KBNR w KQkq - 0 1")

        # Beginner (depth=1, use_quiescence=True, max_quiescence_depth=0, max_check_depth=1)
        res = choose_move(board, difficulty="beginner")

        # Engine must not blunder the queen with Qxf7+
        assert res.best_move_san != "Qxf7+", "Beginner must not sacrifice queen for pawn due to check blindness"
        assert res.best_move in board.legal_moves

    def test_legal_evasions_considered_within_configured_allowance(self) -> None:
        """
        Verifies that when in check at depth 0, legal check evasions are explored
        within the configured check evasion allowance (max_check_depth=1).
        """
        import chess
        from engine.search.alpha_beta import alpha_beta_search

        # White Queen on f3 gives Qxf7+
        board = chess.Board("rnbqkbnr/pppp1ppp/8/8/8/5Q2/PPPPP1PP/RNB1KBNR w KQkq - 0 1")
        board.push_san("Qxf7+")
        assert board.is_check()

        # At depth 0 with max_check_depth=1, Black evaluates evasion Kxf7 -> score strongly favors Black
        res_with_evasion = alpha_beta_search(
            board, depth=1, use_quiescence=True, max_quiescence_depth=0, max_check_depth=1
        )
        assert res_with_evasion.score_cp < -500, f"Expected score favoring Black after queen capture, got {res_with_evasion.score_cp}"

    def test_unresolved_check_fallback_at_emergency_boundary(self) -> None:
        """
        Verifies that UNRESOLVED_CHECK_PENALTY is applied strictly at the emergency
        boundary (max_check_depth=0) and not when legal evasions can resolve check.
        """
        import chess
        from engine.constants import UNRESOLVED_CHECK_PENALTY
        from engine.evaluation.evaluator import evaluate_position
        from engine.search.alpha_beta import _alpha_beta
        from engine.search.ordering import SearchContext

        board = chess.Board("rnbqkbnr/pppp1ppp/8/8/8/5Q2/PPPPP1PP/RNB1KBNR w KQkq - 0 1")
        board.push_san("Qxf7+")
        assert board.is_check()

        static_eval = evaluate_position(board)

        # At depth 0 with max_check_depth=0, Black is in check with 0 evasion allowance -> penalized by UNRESOLVED_CHECK_PENALTY
        score_emergency, _ = _alpha_beta(
            board=board,
            depth=0,
            ply=1,
            alpha=-30000,
            beta=30000,
            config=None,
            context=SearchContext(),
            use_move_ordering=False,
            use_quiescence=True,
            max_quiescence_depth=0,
            max_check_depth=0,
        )
        # Since Black is in check, White receives static_eval + UNRESOLVED_CHECK_PENALTY
        expected_penalized = static_eval + UNRESOLVED_CHECK_PENALTY
        assert score_emergency == expected_penalized, f"Expected {expected_penalized}, got {score_emergency}"

        # In contrast, with max_check_depth=1, Black can search legal check evasion (Kxf7)
        score_with_evasion, _ = _alpha_beta(
            board=board,
            depth=0,
            ply=1,
            alpha=-30000,
            beta=30000,
            config=None,
            context=SearchContext(),
            use_move_ordering=False,
            use_quiescence=True,
            max_quiescence_depth=0,
            max_check_depth=1,
        )
        assert score_with_evasion < -500, f"Expected score favoring Black after queen capture, got {score_with_evasion}"

    def test_board_restored_after_interruption_during_check_search(self) -> None:
        """
        Verifies that the board state is 100% restored if search is interrupted
        while evaluating legal check evasions.
        """
        import chess
        from engine.search.alpha_beta import alpha_beta_search

        # Position with active check: Queen checking King
        check_fen = "rnb1kbnr/ppppqppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"
        board = chess.Board(check_fen)
        fen_before = board.fen()

        # Interrupt search with an extremely tight node budget
        res = alpha_beta_search(
            board, depth=2, max_nodes=5, use_quiescence=False, max_check_depth=1
        )

        assert board.fen() == fen_before, "Board state corrupted after interrupted search"
        assert res.is_interrupted is True
        assert res.best_move in board.legal_moves, "Returned move must be legal"

    def test_beginner_returns_legal_moves_under_check(self) -> None:
        """
        Verifies that Beginner difficulty always returns a valid legal move
        when the side to move is currently in check.
        """
        import chess
        from engine import choose_move

        # Check positions
        check_positions = [
            "rnb1kbnr/ppppqppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1",  # Queen check
            "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1",                            # Rook check
            "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR b KQkq - 3 3", # Mate threat
        ]

        for fen in check_positions:
            b = chess.Board(fen)
            res = choose_move(b, difficulty="beginner")
            assert res.best_move is not None, f"No move returned for FEN: {fen}"
            assert res.best_move in b.legal_moves, f"Illegal move {res.best_move} returned for FEN: {fen}"
