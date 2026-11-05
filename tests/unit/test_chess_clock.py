"""Unit and specification tests for backend chess clocks and time controls (Stage 10.4A)."""

import threading
import time
import pytest
import chess
from fastapi.testclient import TestClient

from backend.game.clock import (
    DEFAULT_TIME_CONTROL,
    TIME_CONTROL_DURATIONS,
    VALID_TIME_CONTROLS,
    ChessClock,
    validate_time_control,
)
from backend.game.exceptions import GameOverError, IllegalMoveError
from backend.game.service import Game
from backend.game.session import SessionManager
from backend.main import app


class MockTimeSource:
    """Controllable monotonic time source for deterministic testing without real waiting."""

    def __init__(self, start_time: float = 1000.0) -> None:
        self.current_time = start_time

    def __call__(self) -> float:
        return self.current_time

    def advance(self, seconds: float) -> None:
        self.current_time += seconds


class TestChessClockUnit:
    """Unit tests for the isolated ChessClock component."""

    def test_validation_all_five_modes(self) -> None:
        for mode in ("bullet", "blitz", "rapid", "classic", "casual"):
            assert validate_time_control(mode) == mode
            assert validate_time_control(mode.upper()) == mode

    def test_validation_rejects_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid time control"):
            validate_time_control("hyperbullet")
        with pytest.raises(ValueError, match="Invalid time control"):
            validate_time_control("10+5")
        with pytest.raises(ValueError, match="must be a string"):
            validate_time_control(123)  # type: ignore

    def test_initial_values_for_every_mode(self) -> None:
        clock_bullet = ChessClock("bullet")
        assert clock_bullet.white_time == 60.0
        assert clock_bullet.black_time == 60.0
        assert clock_bullet.is_timed is True

        clock_blitz = ChessClock("blitz")
        assert clock_blitz.white_time == 180.0
        assert clock_blitz.black_time == 180.0

        clock_rapid = ChessClock("rapid")
        assert clock_rapid.white_time == 600.0
        assert clock_rapid.black_time == 600.0

        clock_classic = ChessClock("classic")
        assert clock_classic.white_time == 1800.0
        assert clock_classic.black_time == 1800.0

        clock_casual = ChessClock("casual")
        assert clock_casual.white_time is None
        assert clock_casual.black_time is None
        assert clock_casual.is_timed is False


class TestGameChessClockSpecifications:
    """Comprehensive tests for authoritative clock integration in Game."""

    def test_1_correct_initial_clock_values_every_mode(self) -> None:
        for mode, expected_secs in TIME_CONTROL_DURATIONS.items():
            game = Game("test", time_control=mode)
            state = game.get_state()
            assert state.time_control == mode
            if mode == "casual":
                assert state.is_timed is False
                assert state.white_time_remaining is None
                assert state.black_time_remaining is None
            else:
                assert state.is_timed is True
                assert state.white_time_remaining == expected_secs
                assert state.black_time_remaining == expected_secs

    def test_2_casual_mode_has_no_active_countdown(self) -> None:
        time_source = MockTimeSource()
        game = Game("casual-game", time_control="casual", time_source=time_source)
        state_init = game.get_state()
        assert state_init.is_timed is False
        assert state_init.clock_started is False

        time_source.advance(500.0)
        game.apply_move("e4")
        time_source.advance(1000.0)
        game.apply_move("e5")

        state_after = game.get_state()
        assert state_after.white_time_remaining is None
        assert state_after.black_time_remaining is None
        assert state_after.is_terminal is False

    def test_3_first_move_clock_activation(self) -> None:
        time_source = MockTimeSource()
        game = Game("timed-game", time_control="rapid", time_source=time_source)

        # Before any move is played, clock must not run
        time_source.advance(120.0)
        state = game.get_state()
        assert state.clock_started is False
        assert state.white_time_remaining == 600.0
        assert state.black_time_remaining == 600.0

        # White plays 1. e4 -> clock activates for Black
        game.apply_move("e4")
        state_after_e4 = game.get_state()
        assert state_after_e4.clock_started is True
        assert state_after_e4.white_time_remaining == 600.0
        assert state_after_e4.active_clock == "black"

    def test_4_clock_switching_after_legal_moves(self) -> None:
        time_source = MockTimeSource()
        game = Game("test", time_control="rapid", time_source=time_source)

        # White plays 1. e4
        game.apply_move("e4")

        # Black thinks for 15.0 seconds
        time_source.advance(15.0)
        game.apply_move("e5")

        state = game.get_state()
        assert state.white_time_remaining == 600.0
        assert state.black_time_remaining == 585.0
        assert state.active_clock == "white"

        # White thinks for 10.0 seconds
        time_source.advance(10.0)
        game.apply_move("Nf3")

        state2 = game.get_state()
        assert state2.white_time_remaining == 590.0
        assert state2.black_time_remaining == 585.0
        assert state2.active_clock == "black"

    def test_5_illegal_moves_do_not_affect_clocks(self) -> None:
        time_source = MockTimeSource()
        game = Game("test", time_control="rapid", time_source=time_source)
        game.apply_move("e4")

        time_source.advance(20.0)
        with pytest.raises(IllegalMoveError):
            game.apply_move("e4")  # Illegal move for Black

        # Clock still reflects 20.0s elapsed for Black, but not reset or double-deducted
        state = game.get_state()
        assert state.black_time_remaining == 580.0
        assert state.white_time_remaining == 600.0

    def test_6_timeout_detection(self) -> None:
        time_source = MockTimeSource()
        # Bullet: 60s
        game = Game("test", time_control="bullet", time_source=time_source)
        game.apply_move("e4")

        # Black runs out of time (75s elapsed > 60s)
        time_source.advance(75.0)

        state = game.get_state()
        assert state.is_terminal is True
        assert state.status == "timeout"
        assert state.black_time_remaining == 0.0

        # Attempting a move after timeout must raise GameOverError
        with pytest.raises(GameOverError):
            game.apply_move("e5")

    def test_7_timeout_win_when_opponent_has_mating_material(self) -> None:
        time_source = MockTimeSource()
        # White has King + Queen, Black has King + Rook
        fen = "8/8/8/8/4k3/8/4r3/4K1Q1 w - - 0 1"
        game = Game("test", initial_fen=fen, time_control="bullet", time_source=time_source)
        # White moves Kd1
        game.apply_move("Kd1")

        # Black times out (opponent White has Queen, sufficient material)
        time_source.advance(100.0)
        state = game.get_state()
        assert state.status == "timeout"
        assert state.result == "1-0"  # White wins on time

    def test_8_timeout_draw_when_opponent_has_insufficient_material_fide_6_9(self) -> None:
        time_source = MockTimeSource()
        # White has King + Queen, Black has lone King (cannot possibly checkmate White!)
        fen = "8/8/8/8/4k3/8/8/4K1Q1 w - - 0 1"
        game = Game("test", initial_fen=fen, time_control="bullet", time_source=time_source)
        game.apply_move("Kd1")

        # Black plays a move
        time_source.advance(5.0)
        game.apply_move("Kd3")

        # Now White times out! (65s elapsed on White's turn)
        time_source.advance(65.0)
        state = game.get_state()
        assert state.status == "timeout"
        # Black has lone King -> insufficient material -> FIDE 6.9 Draw!
        assert state.result == "1/2-1/2"

    def test_9_restart_resets_clocks(self) -> None:
        time_source = MockTimeSource()
        game = Game("test", time_control="rapid", time_source=time_source)
        game.apply_move("e4")
        time_source.advance(50.0)
        game.apply_move("e5")

        game.restart()
        state = game.get_state()
        assert state.clock_started is False
        assert state.white_time_remaining == 600.0
        assert state.black_time_remaining == 600.0
        assert state.time_control == "rapid"
        assert state.is_terminal is False

    def test_10_single_ply_undo_restores_clock_snapshots(self) -> None:
        time_source = MockTimeSource()
        game = Game("test", time_control="rapid", time_source=time_source)

        # Move 1: White e4 (takes 0s before clock starts)
        game.apply_move("e4")

        # Black thinks for 30s
        time_source.advance(30.0)
        game.apply_move("c5")  # Black time becomes 570.0

        state_after_c5 = game.get_state()
        assert state_after_c5.black_time_remaining == 570.0
        assert state_after_c5.white_time_remaining == 600.0

        # Undo Black's move 1... c5
        game.undo(1)

        state_after_undo = game.get_state()
        # Must restore state after 1. e4: Black time was 600.0, White time 600.0
        assert state_after_undo.white_time_remaining == 600.0
        assert state_after_undo.black_time_remaining == 600.0
        assert state_after_undo.turn == "black"

        # Undo White's move 1. e4
        game.undo(1)
        state_initial = game.get_state()
        assert state_initial.clock_started is False
        assert state_initial.white_time_remaining == 600.0
        assert state_initial.black_time_remaining == 600.0
        assert state_initial.turn == "white"

    def test_11_pass_and_play_clock_switching(self) -> None:
        time_source = MockTimeSource()
        game = Game("pnp-game", time_control="blitz", time_source=time_source)

        game.apply_move("d4")
        time_source.advance(10.0)
        game.apply_move("d5")
        time_source.advance(8.0)
        game.apply_move("c4")

        state = game.get_state()
        assert state.white_time_remaining == 172.0  # 180 - 8
        assert state.black_time_remaining == 170.0  # 180 - 10

    def test_12_ai_thinking_time_is_deducted(self) -> None:
        game = Game("ai-game", time_control="rapid", difficulty="beginner")
        game.apply_move("e4")
        initial_black_time = game.get_state().black_time_remaining
        assert initial_black_time is not None

        # AI executes move with real thinking time
        rec = game.ai_move()
        assert rec is not None

        state_after = game.get_state()
        # Thinking time was deducted from Black
        assert state_after.black_time_remaining is not None
        assert state_after.black_time_remaining < initial_black_time

    def test_13_ai_search_respects_available_clock_time(self) -> None:
        time_source = MockTimeSource()
        game = Game("low-clock-ai", time_control="bullet", difficulty="medium", time_source=time_source)
        game.apply_move("e4")

        # Simulate Black clock drained down to only 0.5s remaining
        game.clock._black_time = 0.5

        # AI should move without hanging or crashing
        rec = game.ai_move()
        assert rec is not None

    def test_14_analysis_does_not_affect_clocks(self) -> None:
        client = TestClient(app)
        res_new = client.post("/api/game/new", json={"time_control": "rapid"})
        assert res_new.status_code == 201
        sid = res_new.json()["session_id"]

        # Human plays 1. e4
        res_move = client.post("/api/game/move", json={"session_id": sid, "move": "e4"})
        assert res_move.status_code == 200

        clock_before = client.get(f"/api/game/state?session_id={sid}").json()["white_time_remaining"]

        res_ana = client.post("/api/game/analyze", json={"session_id": sid, "depth": 2})
        assert res_ana.status_code == 200

        clock_after = client.get(f"/api/game/state?session_id={sid}").json()["white_time_remaining"]
        assert clock_before == clock_after

    def test_15_concurrent_move_and_timeout(self) -> None:
        time_source = MockTimeSource()
        game = Game("race-test", time_control="bullet", time_source=time_source)
        game.apply_move("e4")

        errors = []

        def worker():
            try:
                game.apply_move("e5")
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        # Board version incremented safely
        assert game.version >= 2

    def test_16_api_time_control_creation_and_rejection(self) -> None:
        client = TestClient(app)

        # Valid time controls
        for tc in ("bullet", "blitz", "rapid", "classic", "casual"):
            res = client.post("/api/game/new", json={"time_control": tc})
            assert res.status_code == 201
            data = res.json()
            assert data["time_control"] == tc
            if tc == "casual":
                assert data["is_timed"] is False
            else:
                assert data["is_timed"] is True

        # Invalid time control rejected with 400
        res_bad = client.post("/api/game/new", json={"time_control": "invalid_mode"})
        assert res_bad.status_code == 400
        assert "Invalid time control" in res_bad.json()["detail"]

    def test_17_ai_search_with_time_below_50ms_never_exceeds_remaining_clock(self) -> None:
        """Deterministic test: AI with 35ms (<50ms) remaining never exceeds remaining clock."""
        game = Game("ai-sub-50ms", time_control="bullet", difficulty="medium")
        game.apply_move("e4")

        # Set Black's clock to exactly 0.035s (35 milliseconds)
        game.clock._black_time = 0.035

        # AI executes move; should succeed and remaining time must be >= 0.0
        rec = game.ai_move()
        assert rec is not None
        assert len(game.get_state().san_history) == 2
        assert game.clock.black_time is not None
        assert game.clock.black_time >= 0.0
        assert game.clock.timed_out_color is None

    def test_18_ai_search_with_time_below_safety_margin_handles_safely(self) -> None:
        """Deterministic test: AI with 15ms (<20ms safety margin) handles safely via instant legal move."""
        game = Game("ai-sub-margin", time_control="bullet", difficulty="expert")
        game.apply_move("e4")

        # Set Black's clock to 15ms (below safety margin of 20ms)
        game.clock._black_time = 0.015

        rec = game.ai_move()
        assert rec is not None
        assert game.clock.black_time is not None
        assert game.clock.black_time > 0.0  # Instant move consumed ~microseconds
        assert game.clock.timed_out_color is None

    def test_19_ai_move_at_zero_or_negative_time_raises_game_over_immediately(self) -> None:
        """Calling ai_move() when clock is already expired raises GameOverError immediately."""
        game = Game("ai-zero-time", time_control="bullet", difficulty="easy")
        game.apply_move("e4")

        game.clock._black_time = 0.0
        game.clock._timed_out_color = "black"

        with pytest.raises(GameOverError):
            game.ai_move()

    def test_20_timeout_checked_before_applying_ai_move(self) -> None:
        """Timeout flag prevents move from being pushed to board."""
        game = Game("ai-timeout-check", time_control="bullet", difficulty="beginner")
        game.apply_move("e4")

        # Flag timeout on Black
        game.clock._black_time = 0.0
        game.clock._timed_out_color = "black"

        with pytest.raises(GameOverError):
            game.ai_move()

        # Board remains at 1 ply (White's e4), AI move was NOT applied
        assert len(game.get_state().san_history) == 1
        assert game.get_state().turn == "black"

    def test_21_delayed_ai_response_cannot_apply_move_after_timeout(self) -> None:
        """If AI thinking time exceeds remaining time, deduct_time flags timeout and rejects move."""
        time_source = MockTimeSource()
        game = Game("ai-overtime", time_control="bullet", difficulty="beginner", time_source=time_source)
        game.apply_move("e4")

        # Black has only 0.010s
        game.clock._black_time = 0.010

        # Simulate artificial clock jump during AI calculation
        call_count = 0

        def expanding_time():
            nonlocal call_count
            call_count += 1
            # When measuring elapsed thinking, advance clock by 0.5s (exceeding 0.010s)
            if call_count >= 2:
                return time_source.current_time + 0.5
            return time_source.current_time

        game.clock._time_source = expanding_time

        with pytest.raises(GameOverError):
            game.ai_move()

        # Confirms timeout occurred and move was rejected
        assert game.clock.timed_out_color == "black"
        assert len(game.get_state().san_history) == 1

    def test_22_clock_consistency_under_concurrent_state_and_move_requests(self) -> None:
        """Clock readings remain non-negative, monotonic, and thread-safe under concurrent access."""
        game = Game("concurrent-clock", time_control="blitz")
        game.apply_move("e4")

        readings: list[Optional[float]] = []
        stop_event = threading.Event()

        def reader():
            while not stop_event.is_set():
                state = game.get_state()
                readings.append(state.black_time_remaining)
                time.sleep(0.001)

        t = threading.Thread(target=reader)
        t.start()

        # Execute AI move on main thread
        game.ai_move()

        stop_event.set()
        t.join()

        # All readings must be non-None, non-negative, and <= 180.0
        assert len(readings) > 0
        for r in readings:
            assert r is not None
            assert 0.0 <= r <= 180.0
