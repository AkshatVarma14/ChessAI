"""Exceptions for the chess game service."""


class ChessGameError(Exception):
    """Base exception for all chess game errors."""
    pass


class SessionNotFoundError(ChessGameError):
    """Raised when a requested game session ID does not exist."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Game session not found: '{session_id}'")
        self.session_id = session_id


class IllegalMoveError(ChessGameError):
    """Raised when an illegal or malformed move is attempted."""

    def __init__(self, move_str: str, reason: str = "Move is illegal in the current position.") -> None:
        super().__init__(f"Invalid move '{move_str}': {reason}")
        self.move_str = move_str
        self.reason = reason


class InvalidFENError(ChessGameError):
    """Raised when an invalid FEN string is supplied."""

    def __init__(self, fen: str, reason: str = "Malformed or illegal FEN string.") -> None:
        super().__init__(f"Invalid FEN '{fen}': {reason}")
        self.fen = fen
        self.reason = reason


class GameOverError(ChessGameError):
    """Raised when a move is attempted on a game that has already finished."""

    def __init__(self, status: str, result: str) -> None:
        super().__init__(f"Cannot make move: Game is already over ({status}, result: {result}).")
        self.status = status
        self.result = result


class UndoError(ChessGameError):
    """Raised when an undo operation cannot be performed (e.g. empty move history)."""

    def __init__(self, requested_plies: int, available_plies: int) -> None:
        super().__init__(
            f"Cannot undo {requested_plies} plies: only {available_plies} plies in history."
        )
        self.requested_plies = requested_plies
        self.available_plies = available_plies


class StalePositionError(ChessGameError):
    """Raised when an asynchronous AI calculation completes on a position that has since changed."""

    def __init__(self, expected_fen: str, current_fen: str) -> None:
        super().__init__(
            f"Cannot apply AI move: board position changed during calculation "
            f"(expected FEN '{expected_fen}', current FEN '{current_fen}')."
        )
        self.expected_fen = expected_fen
        self.current_fen = current_fen
