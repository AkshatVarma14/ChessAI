"""Game service package managing authoritative chess state and rules arbitration."""

from backend.game.exceptions import (
    ChessGameError,
    GameOverError,
    IllegalMoveError,
    InvalidFENError,
    SessionNotFoundError,
    StalePositionError,
    UndoError,
)
from backend.game.models import (
    Color,
    GameResult,
    GameState,
    GameStatus,
    MoveRecord,
)
from backend.game.service import Game
from backend.game.session import SessionManager

__all__ = [
    "Game",
    "SessionManager",
    "GameState",
    "MoveRecord",
    "GameStatus",
    "GameResult",
    "Color",
    "ChessGameError",
    "SessionNotFoundError",
    "StalePositionError",
    "IllegalMoveError",
    "InvalidFENError",
    "GameOverError",
    "UndoError",
]
