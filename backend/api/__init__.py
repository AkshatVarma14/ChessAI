"""API package exposing FastAPI routers and schemas."""

from backend.api.routes.game import router as game_router
from backend.api.schemas import (
    ErrorResponse,
    GameState,
    MakeMoveRequest,
    MoveRecord,
    NewGameRequest,
    RestartGameRequest,
    UndoMoveRequest,
)

__all__ = [
    "game_router",
    "NewGameRequest",
    "MakeMoveRequest",
    "UndoMoveRequest",
    "RestartGameRequest",
    "ErrorResponse",
    "GameState",
    "MoveRecord",
]
