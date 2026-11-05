"""FastAPI dependency providers."""

from functools import lru_cache
from backend.game.session import SessionManager


@lru_cache()
def get_session_manager() -> SessionManager:
    """Provides a singleton SessionManager instance across API requests."""
    return SessionManager()
