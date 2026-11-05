"""Pydantic schemas for FastAPI API endpoints."""

from typing import List, Optional
from pydantic import BaseModel, Field

from backend.game.models import GameState, MoveRecord

__all__ = [
    "NewGameRequest",
    "MakeMoveRequest",
    "UndoMoveRequest",
    "RestartGameRequest",
    "DifficultyUpdateRequest",
    "AIMoveRequest",
    "AnalyzePositionRequest",
    "AnalysisResponse",
    "PGNResponse",
    "ErrorResponse",
    "GameState",
    "MoveRecord",
]


class NewGameRequest(BaseModel):
    """Request payload to initialize a new chess game session."""

    initial_fen: Optional[str] = Field(
        None,
        description="Optional custom FEN setup string. If omitted, standard starting position is used.",
    )
    difficulty: Optional[str] = Field(
        "medium",
        description="Engine difficulty preset ('beginner', 'easy', 'medium', 'hard', 'expert'). Defaults to 'medium'.",
    )
    time_control: Optional[str] = Field(
        "rapid",
        description="Time control preset ('bullet', 'blitz', 'rapid', 'classic', 'casual'). Defaults to 'rapid'.",
    )


class DifficultyUpdateRequest(BaseModel):
    """Request payload to change difficulty preset in an active session."""

    session_id: str = Field(..., description="Active session identifier")
    difficulty: str = Field(
        ...,
        description="Target engine difficulty preset ('beginner', 'easy', 'medium', 'hard', 'expert')",
    )


class AIMoveRequest(BaseModel):
    """Request payload to trigger an automated AI move in an active session."""

    session_id: str = Field(..., description="Active session identifier")


class MakeMoveRequest(BaseModel):
    """Request payload to execute a move in an active game session."""

    session_id: str = Field(..., description="Active session identifier")
    move: str = Field(
        ...,
        description="Chess move in UCI (e.g. 'e2e4', 'e7e8q') or SAN (e.g. 'e4', 'Nf3', 'O-O') notation",
    )


class UndoMoveRequest(BaseModel):
    """Request payload to revert plies in an active game session."""

    session_id: str = Field(..., description="Active session identifier")
    plies: int = Field(
        default=1,
        ge=1,
        description="Number of half-moves (plies) to revert. Defaults to 1.",
    )


class RestartGameRequest(BaseModel):
    """Request payload to restart an active game session to initial state."""

    session_id: str = Field(..., description="Active session identifier")


class AnalyzePositionRequest(BaseModel):
    """Request payload to analyze a chess position via the custom engine."""

    session_id: Optional[str] = Field(None, description="Optional active session ID to analyze current session board")
    fen: Optional[str] = Field(None, description="Optional FEN string to analyze (takes precedence if provided)")
    depth: Optional[int] = Field(default=None, ge=1, le=8, description="Target search depth (1-8). Defaults to profile depth or 3.")
    time_limit_ms: Optional[float] = Field(default=None, ge=100.0, le=10000.0, description="Search time limit in ms. Defaults to profile limit or 1500.0ms.")
    difficulty: Optional[str] = Field(None, description="Optional difficulty preset for analysis")


class AnalysisResponse(BaseModel):
    """Engine analysis results for position evaluation, PV, and statistics."""

    score_cp: int = Field(..., description="Evaluation score in centipawns from White's perspective")
    is_mate: bool = Field(default=False, description="True if position has a forced checkmate")
    mate_in_plies: Optional[int] = Field(None, description="Number of plies to forced mate if applicable")
    is_terminal: bool = Field(default=False, description="True if position is automatically terminal")
    claimable_draw: Optional[str] = Field(default=None, description="Type of draw that can be claimed ('fifty_moves', 'threefold_repetition') if applicable")
    depth: int = Field(..., description="Completed search depth")
    nodes_searched: int = Field(..., description="Total search nodes visited")
    quiescence_nodes: int = Field(default=0, description="Nodes evaluated in quiescence search")
    elapsed_ms: float = Field(..., description="Elapsed search time in milliseconds")
    nodes_per_second: int = Field(..., description="Engine search speed in nodes per second")
    best_move_uci: Optional[str] = Field(None, description="Best recommended move in UCI format")
    best_move_san: Optional[str] = Field(None, description="Best recommended move in SAN format")
    pv_uci: List[str] = Field(default_factory=list, description="Principal Variation move sequence in UCI format")
    pv_san: List[str] = Field(default_factory=list, description="Principal Variation move sequence in SAN format")
    tt_hits: int = Field(default=0, description="Transposition table cache hits")
    tt_probes: int = Field(default=0, description="Transposition table probes")
    tt_cutoffs: int = Field(default=0, description="Transposition table beta cutoffs")
    tt_stores: int = Field(default=0, description="Transposition table stores")


class ClaimDrawRequest(BaseModel):
    """Request payload to claim a draw by threefold repetition or 50-move rule."""

    session_id: str = Field(..., description="Active session identifier")


class PGNResponse(BaseModel):
    """PGN export response containing standard PGN game text."""

    session_id: str = Field(..., description="Active session identifier")
    pgn: str = Field(..., description="Standard PGN game representation")


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    error: str = Field(..., description="Error classification or summary")
    detail: Optional[str] = Field(None, description="Detailed explanation of the failure")
    session_id: Optional[str] = Field(None, description="Associated session ID if applicable")
