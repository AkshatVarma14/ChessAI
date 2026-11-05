"""In-memory session manager for isolated chess games."""

from typing import Dict, List, Optional
import uuid

from backend.game.exceptions import SessionNotFoundError
from backend.game.models import GameState
from backend.game.service import Game


class SessionManager:
    """
    Manages active chess game sessions.
    
    Guarantees isolation: each session maintains an independent Game instance
    backed by its own authoritative chess.Board.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, Game] = {}

    def create_session(
        self,
        initial_fen: Optional[str] = None,
        session_id: Optional[str] = None,
        difficulty: str = "medium",
        time_control: str = "rapid",
        time_source: Optional[callable] = None,
    ) -> GameState:
        """
        Creates a new isolated game session.
        
        Args:
            initial_fen: Optional starting FEN. If None, uses standard chess starting position.
            session_id: Optional explicit session ID; if omitted, generates a unique UUID4 string.
            difficulty: Engine difficulty preset ('beginner', 'easy', 'medium', 'hard', 'expert').
            time_control: Time control preset ('bullet', 'blitz', 'rapid', 'classic', 'casual').
            time_source: Optional monotonic clock callable for testing.
            
        Returns:
            Initial GameState of the newly created session.
        """
        sid = session_id or str(uuid.uuid4())
        game = Game(
            session_id=sid,
            initial_fen=initial_fen,
            difficulty=difficulty,
            time_control=time_control,
            time_source=time_source,
        )
        self._sessions[sid] = game
        return game.get_state()

    def get_game(self, session_id: str) -> Game:
        """
        Retrieves the underlying Game instance for a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Game instance.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        game = self._sessions.get(session_id)
        if game is None:
            raise SessionNotFoundError(session_id)
        return game

    def get_state(self, session_id: str) -> GameState:
        """
        Retrieves the current GameState snapshot for a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Current GameState.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        return self.get_game(session_id).get_state()

    def make_move(self, session_id: str, move_str: str) -> GameState:
        """
        Applies a move to a specific session and returns updated state.
        
        Args:
            session_id: Session identifier.
            move_str: Move in UCI or SAN format.
            
        Returns:
            Updated GameState.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
            IllegalMoveError: If the move is invalid or illegal.
            GameOverError: If the game has already concluded.
        """
        game = self.get_game(session_id)
        game.apply_move(move_str)
        return game.get_state()

    def make_ai_move(self, session_id: str) -> GameState:
        """
        Executes an AI move on behalf of the active player using the engine difficulty.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Updated GameState.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
            GameOverError: If the game has already concluded.
        """
        game = self.get_game(session_id)
        game.ai_move()
        return game.get_state()

    def set_difficulty(self, session_id: str, difficulty: str) -> GameState:
        """
        Updates the engine difficulty preset for an active session.
        
        Args:
            session_id: Session identifier.
            difficulty: Case-insensitive difficulty preset string.
            
        Returns:
            Updated GameState.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
            ValueError: If the difficulty level is unsupported.
        """
        game = self.get_game(session_id)
        game.set_difficulty(difficulty)
        return game.get_state()

    def undo_move(self, session_id: str, plies: int = 1) -> GameState:
        """
        Reverts plies from the session's move history.
        
        Args:
            session_id: Session identifier.
            plies: Number of half-moves to revert (default 1).
            
        Returns:
            Updated GameState after undo.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
            UndoError: If plies exceed available history.
        """
        game = self.get_game(session_id)
        game.undo(plies=plies)
        return game.get_state()

    def claim_draw(self, session_id: str) -> GameState:
        """
        Claims a draw for the active session if eligible by 50-move rule or threefold repetition.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Updated GameState after claiming draw.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
            GameOverError: If the game has already concluded.
            IllegalMoveError: If no draw can be claimed.
        """
        game = self.get_game(session_id)
        game.claim_draw()
        return game.get_state()

    def restart_session(self, session_id: str) -> GameState:
        """
        Resets a session back to its initial position.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Reset GameState.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        game = self.get_game(session_id)
        game.restart()
        return game.get_state()

    def get_pgn(self, session_id: str) -> str:
        """
        Generates standard PGN string for the specified session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            PGN text representation.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        game = self.get_game(session_id)
        return game.get_pgn()

    def delete_session(self, session_id: str) -> bool:
        """
        Removes a session from memory.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            True if removed.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id)
        del self._sessions[session_id]
        return True

    def session_exists(self, session_id: str) -> bool:
        """Checks if a session ID exists in active memory."""
        return session_id in self._sessions

    def list_sessions(self) -> List[str]:
        """Returns all active session identifiers."""
        return list(self._sessions.keys())

    def count(self) -> int:
        """Returns total active session count."""
        return len(self._sessions)

    def clear(self) -> None:
        """Deletes all active sessions."""
        self._sessions.clear()
