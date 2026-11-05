"""Unit tests for dynamic time management and search budget allocation."""

import chess
import pytest

from engine.difficulty import DIFFICULTY_PROFILES, DifficultyLevel
from engine.search.time_manager import DEFAULT_SAFETY_MARGIN_MS, TimeManager


class TestTimeManager:
    """Tests dynamic time allocation, safety margins, and early termination heuristics."""

    def test_invalid_safety_margin_raises(self) -> None:
        """Negative safety margin is rejected."""
        with pytest.raises(ValueError, match="safety_margin_ms must be non-negative"):
            TimeManager(safety_margin_ms=-5.0)

    def test_single_legal_move_allocates_min_time(self) -> None:
        """When only 1 legal move exists, allocated time is strictly min_time_ms."""
        tm = TimeManager()
        profile = DIFFICULTY_PROFILES[DifficultyLevel.HARD]

        # White pawn can only move to e8, king on a1 blocked, no other moves
        # FEN: 8/4P3/8/8/8/8/8/k6K w - - 0 1 (only e8=Q/R/B/N moves, let's craft exact 1 move)
        # Position with exactly 1 legal move: King in check with single evasion
        # White king on h1 in check by rook on h8, pawn on g2 blocks escape to g1, g2 pinned or blocked
        board = chess.Board("7r/8/8/8/8/6P1/6P1/7K w - - 0 1")
        assert board.legal_moves.count() == 1  # Only Kh2 or Kg1? Let's check:
        # On h1, Kh2 is legal. g1 is blocked? No, let's verify exact legal move count
        moves = list(board.legal_moves)
        assert len(moves) == 1

        allocated = tm.allocate_time(board, profile)
        assert allocated == profile.min_time_ms

    def test_allocations_bounded_by_profile_limits(self) -> None:
        """Allocated time must strictly adhere to [min_time_ms, max_time_ms] across all profiles."""
        tm = TimeManager()
        board = chess.Board()

        for level, profile in DIFFICULTY_PROFILES.items():
            allocated = tm.allocate_time(board, profile)
            assert profile.min_time_ms <= allocated <= profile.max_time_ms, (
                f"Profile {level} allocated {allocated} outside [{profile.min_time_ms}, {profile.max_time_ms}]"
            )

    def test_check_boost_increases_allocation(self) -> None:
        """A position with the king in check receives a tactical urgency boost."""
        tm = TimeManager()
        profile = DIFFICULTY_PROFILES[DifficultyLevel.MEDIUM]

        # Non-check position with open e-file
        normal_board = chess.Board("rnb1kbnr/pppp1ppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1")
        assert not normal_board.is_check()
        normal_alloc = tm.allocate_time(normal_board, profile)

        # Check position with queen delivering check on open e-file (multiple legal evasions)
        check_board = chess.Board("rnb1kbnr/ppppqppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1")
        assert check_board.is_check()
        assert check_board.legal_moves.count() > 1
        check_alloc = tm.allocate_time(check_board, profile)

        # Check allocation should be boosted
        assert check_alloc > normal_alloc

    def test_game_phase_scaling(self) -> None:
        """Middlegame positions receive higher budget than late endgames."""
        tm = TimeManager()
        profile = DIFFICULTY_PROFILES[DifficultyLevel.HARD]

        # Complex middlegame (equal moves roughly)
        middlegame_board = chess.Board("r2q1rk1/1b2bppp/p1n1pn2/1pp5/3PP3/2NB1N2/PP3PPP/R1BQR1K1 w - - 0 12")

        # Simplified rook endgame
        endgame_board = chess.Board("8/5pk1/4p1p1/7p/3R3P/6P1/5PK1/4r3 w - - 0 40")

        mg_alloc = tm.allocate_time(middlegame_board, profile)
        eg_alloc = tm.allocate_time(endgame_board, profile)

        assert mg_alloc > eg_alloc

    def test_effective_search_limit_reserves_safety_margin(self) -> None:
        """Ensures effective limit deducts safety margin and never drops below min_time_ms."""
        tm = TimeManager(safety_margin_ms=50.0)

        # High budget: 1000 - 50 = 950
        eff = tm.get_effective_search_limit(allocated_time_ms=1000.0, min_time_ms=100.0)
        assert eff == 950.0

        # Low budget near min: 120 - 50 = 70 < min (100) -> clamped to 100
        eff_clamped = tm.get_effective_search_limit(allocated_time_ms=120.0, min_time_ms=100.0)
        assert eff_clamped == 100.0

    def test_should_terminate_early_depth_under_2_never_stops(self) -> None:
        """Depth 0 or 1 never triggers early exit."""
        tm = TimeManager()
        assert tm.should_terminate_early(elapsed_ms=500.0, allocated_ms=600.0, completed_depth=1) is False
        assert tm.should_terminate_early(elapsed_ms=500.0, allocated_ms=600.0, completed_depth=0) is False

    def test_should_terminate_early_over_60_percent_ratio(self) -> None:
        """When elapsed time exceeds 60% of allocation at depth >= 2, early stop is advised."""
        tm = TimeManager()
        # 650ms / 1000ms = 65% >= 60%
        assert tm.should_terminate_early(elapsed_ms=650.0, allocated_ms=1000.0, completed_depth=2) is True

        # 300ms / 1000ms = 30% < 60%
        assert tm.should_terminate_early(elapsed_ms=300.0, allocated_ms=1000.0, completed_depth=2) is False

    def test_should_terminate_early_stable_pv(self) -> None:
        """Stable PV over 2+ iterations at depth >= 3 with small score diff triggers early exit at >= 40%."""
        tm = TimeManager()

        # Depth 3, PV stable 2 iterations, score diff 10 cp, 45% time consumed
        assert (
            tm.should_terminate_early(
                elapsed_ms=450.0,
                allocated_ms=1000.0,
                completed_depth=3,
                pv_stable_iterations=2,
                score_diff_cp=10,
            )
            is True
        )

        # Depth 3, PV unstable (only 1 iteration stable), 45% time consumed -> does not terminate
        assert (
            tm.should_terminate_early(
                elapsed_ms=450.0,
                allocated_ms=1000.0,
                completed_depth=3,
                pv_stable_iterations=1,
                score_diff_cp=10,
            )
            is False
        )
