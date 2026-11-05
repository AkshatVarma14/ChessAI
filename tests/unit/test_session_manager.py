"""Unit tests for the SessionManager."""

import pytest

from backend.game.exceptions import SessionNotFoundError
from backend.game.session import SessionManager


class TestSessionManager:
    """Test lifecycle, multi-session isolation, and error handling."""

    def test_create_and_retrieve_session(self) -> None:
        manager = SessionManager()
        state = manager.create_session()
        assert state.session_id is not None
        assert state.status == "active"
        assert manager.count() == 1
        assert manager.session_exists(state.session_id)

        # Retrieve state
        fetched = manager.get_state(state.session_id)
        assert fetched.session_id == state.session_id
        assert fetched.fen == state.fen

    def test_create_session_with_explicit_id(self) -> None:
        manager = SessionManager()
        state = manager.create_session(session_id="custom-id-123")
        assert state.session_id == "custom-id-123"
        assert manager.session_exists("custom-id-123")

    def test_nonexistent_session_raises_error(self) -> None:
        manager = SessionManager()
        with pytest.raises(SessionNotFoundError) as exc_info:
            manager.get_state("nonexistent-id")
        assert exc_info.value.session_id == "nonexistent-id"

        with pytest.raises(SessionNotFoundError):
            manager.make_move("nonexistent-id", "e4")

        with pytest.raises(SessionNotFoundError):
            manager.undo_move("nonexistent-id")

        with pytest.raises(SessionNotFoundError):
            manager.restart_session("nonexistent-id")

        with pytest.raises(SessionNotFoundError):
            manager.delete_session("nonexistent-id")

    def test_multi_session_isolation(self) -> None:
        """Verify that moves in Session A do not leak into or affect Session B."""
        manager = SessionManager()
        session_a = manager.create_session(session_id="session-a")
        session_b = manager.create_session(session_id="session-b")

        # Play move in Session A
        manager.make_move("session-a", "e4")
        state_a = manager.get_state("session-a")
        state_b = manager.get_state("session-b")

        assert state_a.san_history == ["e4"]
        assert state_a.turn == "black"

        # Session B must remain untouched in the initial starting position
        assert state_b.san_history == []
        assert state_b.turn == "white"
        assert state_b.fen != state_a.fen

        # Play different move in Session B
        manager.make_move("session-b", "d4")
        state_b_updated = manager.get_state("session-b")
        assert state_b_updated.san_history == ["d4"]
        assert state_b_updated.turn == "black"

        # Session A still has only e4
        state_a_refetched = manager.get_state("session-a")
        assert state_a_refetched.san_history == ["e4"]

    def test_session_undo_and_restart(self) -> None:
        manager = SessionManager()
        manager.create_session(session_id="session-ops")
        manager.make_move("session-ops", "e4")
        manager.make_move("session-ops", "e5")

        state = manager.get_state("session-ops")
        assert len(state.san_history) == 2

        # Undo 1 ply
        state_after_undo = manager.undo_move("session-ops", plies=1)
        assert state_after_undo.san_history == ["e4"]

        # Restart session
        state_after_restart = manager.restart_session("session-ops")
        assert len(state_after_restart.san_history) == 0
        assert state_after_restart.turn == "white"

    def test_delete_and_clear_sessions(self) -> None:
        manager = SessionManager()
        manager.create_session(session_id="s1")
        manager.create_session(session_id="s2")
        assert manager.count() == 2

        assert manager.delete_session("s1") is True
        assert not manager.session_exists("s1")
        assert manager.count() == 1

        manager.clear()
        assert manager.count() == 0
        assert manager.list_sessions() == []
