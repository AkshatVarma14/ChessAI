"""Data models and types for the chess game service."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

GameStatus = Literal[
    "active",
    "checkmate",
    "stalemate",
    "draw_insufficient_material",
    "draw_75_moves",
    "draw_fivefold_repetition",
    "draw_50_moves",
    "draw_repetition",
    "draw_claimed",
    "timeout",
]

GameResult = Literal[
    "1-0",
    "0-1",
    "1/2-1/2",
    "*",
]

Color = Literal["white", "black"]


class MoveRecord(BaseModel):
    """Details of a single executed chess move."""

    san: str = Field(..., description="Standard Algebraic Notation (e.g. 'e4', 'Nf3', 'O-O')")
    uci: str = Field(..., description="Universal Chess Interface format (e.g. 'e2e4')")
    from_square: str = Field(..., description="Source square identifier (e.g. 'e2')")
    to_square: str = Field(..., description="Destination square identifier (e.g. 'e4')")
    promotion: Optional[str] = Field(None, description="Promoted piece type if applicable ('q', 'r', 'b', 'n')")
    is_capture: bool = Field(..., description="Whether the move captured a piece or pawn")
    is_check: bool = Field(..., description="Whether the move delivered check")
    ply: int = Field(..., description="1-indexed ply count of this move in the game")


class GameState(BaseModel):
    """Complete snapshot of authoritative game state."""

    session_id: str = Field(..., description="Unique identifier for this game session")
    fen: str = Field(..., description="Current Forsyth-Edwards Notation string")
    turn: Color = Field(..., description="Side whose turn it is to move ('white' or 'black')")
    fullmove_number: int = Field(..., description="Current fullmove number, starting at 1")
    halfmove_clock: int = Field(..., description="Halfmove clock for 50-move rule")
    is_check: bool = Field(..., description="True if the active king is in check")
    is_terminal: bool = Field(..., description="True if the game has ended")
    status: GameStatus = Field(..., description="Detailed status of the game")
    result: GameResult = Field(..., description="Official result: '1-0', '0-1', '1/2-1/2', or '*'")
    san_history: List[str] = Field(default_factory=list, description="List of played moves in SAN")
    uci_history: List[str] = Field(default_factory=list, description="List of played moves in UCI")
    fen_history: List[str] = Field(default_factory=list, description="Authoritative history of FENs after each ply, starting from initial position")
    legal_moves_uci: List[str] = Field(default_factory=list, description="List of legal moves in UCI format")
    legal_moves_san: List[str] = Field(default_factory=list, description="List of legal moves in SAN format")
    can_undo: bool = Field(..., description="True if at least one move can be undone")
    difficulty: str = Field(default="medium", description="Active engine difficulty preset")
    can_claim_draw: bool = Field(default=False, description="True if a draw can currently be claimed")
    claimable_draw: Optional[Literal["fifty_moves", "threefold_repetition"]] = Field(
        default=None,
        description="Type of draw that can be claimed ('fifty_moves' or 'threefold_repetition') if applicable",
    )
    time_control: str = Field(
        default="rapid",
        description="Active time control preset ('bullet', 'blitz', 'rapid', 'classic', 'casual')",
    )
    is_timed: bool = Field(
        default=True,
        description="True if game uses countdown clocks (False for Casual)",
    )
    white_time_remaining: Optional[float] = Field(
        default=600.0,
        description="White remaining clock time in seconds (None for Casual)",
    )
    black_time_remaining: Optional[float] = Field(
        default=600.0,
        description="Black remaining clock time in seconds (None for Casual)",
    )
    clock_started: bool = Field(
        default=False,
        description="True if chess clock has started ticking (activated on first legal move)",
    )
    active_clock: Optional[Color] = Field(
        default=None,
        description="Side whose clock is currently active, or None if clock has not started or game ended",
    )
