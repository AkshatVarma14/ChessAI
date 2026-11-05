"""Authoritative Chess Game implementation backed by python-chess."""

import threading
from typing import Callable, List, Literal, Optional
import chess

from backend.game.clock import ChessClock, TimeControlType, validate_time_control
from backend.game.exceptions import (
    GameOverError,
    IllegalMoveError,
    InvalidFENError,
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
from engine import SearchConfig, choose_move, get_difficulty_profile, validate_difficulty


class Game:
    """
    Authoritative stateful representation of a chess game.
    
    Delegates all rules, legal move generation, validation, and terminal state
    arbitration to python-chess. Maintains complete move history for lossless undo
    and state reconstruction.
    """

    def __init__(
        self,
        session_id: str,
        initial_fen: Optional[str] = None,
        difficulty: str = "medium",
        time_control: str = "rapid",
        time_source: Optional[Callable[[], float]] = None,
    ) -> None:
        """
        Initialize a new game.
        
        Args:
            session_id: Unique identifier for this game session.
            initial_fen: Optional FEN string. If omitted, uses standard chess starting position.
            difficulty: Engine difficulty preset ('beginner', 'easy', 'medium', 'hard', 'expert').
            time_control: Time control preset ('bullet', 'blitz', 'rapid', 'classic', 'casual').
            time_source: Optional monotonic time callable for testing.
            
        Raises:
            InvalidFENError: If the provided FEN is invalid or unparseable.
            ValueError: If the difficulty level or time control is unsupported.
        """
        self.session_id = session_id
        self._initial_fen = initial_fen or chess.STARTING_FEN
        self._difficulty = validate_difficulty(difficulty)
        self._clock = ChessClock(time_control=time_control, time_source=time_source)

        try:
            self._board = chess.Board(self._initial_fen)
        except ValueError as err:
            raise InvalidFENError(self._initial_fen, str(err)) from err

        self._move_records: List[MoveRecord] = []
        self._fen_history: List[str] = [self._board.fen()]
        self._version: int = 0
        self._draw_claimed: bool = False
        self._claimed_draw_reason: Optional[str] = None
        self._lock = threading.Lock()

    @property
    def clock(self) -> ChessClock:
        """Authoritative chess clock instance."""
        return self._clock

    @property
    def time_control(self) -> TimeControlType:
        """Active time control preset."""
        return self._clock.time_control

    @property
    def version(self) -> int:
        """Monotonically increasing version counter for board mutation tracking."""
        return self._version

    @property
    def difficulty(self) -> str:
        """Active engine difficulty preset."""
        return self._difficulty

    def set_difficulty(self, difficulty: str) -> None:
        """
        Updates the engine difficulty for subsequent AI moves.
        
        Preserves the current board state and move history.
        
        Args:
            difficulty: Case-insensitive difficulty preset string.
            
        Raises:
            ValueError: If the difficulty level is unsupported.
        """
        self._difficulty = validate_difficulty(difficulty)

    @property
    def board(self) -> chess.Board:
        """Returns a copy of the authoritative internal chess board."""
        with self._lock:
            return self._board.copy()

    @property
    def fen(self) -> str:
        """Current FEN string."""
        return self._board.fen()

    @property
    def turn(self) -> Color:
        """Side to move ('white' or 'black')."""
        return "white" if self._board.turn == chess.WHITE else "black"

    @property
    def fullmove_number(self) -> int:
        """Current fullmove number."""
        return self._board.fullmove_number

    @property
    def halfmove_clock(self) -> int:
        """Current halfmove clock count towards 50-move rule."""
        return self._board.halfmove_clock

    @property
    def is_check(self) -> bool:
        """True if current side's king is in check."""
        return self._board.is_check()

    @property
    def is_terminal(self) -> bool:
        """
        True if the game has reached an automatic terminal state or a claimed draw.
        
        Automatic terminations under FIDE rules include:
        - Checkmate
        - Stalemate
        - Insufficient material / dead position
        - 75-move rule (is_seventyfive_moves)
        - Fivefold repetition (is_fivefold_repetition)
        - Explicitly claimed draw (50-move rule or threefold repetition)
        
        Merely claimable draws (50-move rule or threefold repetition without claim)
        do NOT terminate the game automatically; the game remains active.
        """
        if (
            self._board.is_checkmate()
            or self._board.is_stalemate()
            or self._board.is_insufficient_material()
            or self._board.is_seventyfive_moves()
            or self._board.is_fivefold_repetition()
            or self._draw_claimed
            or self._clock.timed_out_color is not None
        ):
            return True
        return False

    @property
    def can_claim_draw(self) -> bool:
        """True if a draw can currently be claimed and game is not already terminal."""
        if self.is_terminal:
            return False
        return self._board.can_claim_draw()

    @property
    def claimable_draw(self) -> Optional[Literal["fifty_moves", "threefold_repetition"]]:
        """Specific claimable draw rule ('fifty_moves' or 'threefold_repetition') if applicable."""
        if self.is_terminal:
            return None
        if self._board.can_claim_fifty_moves():
            return "fifty_moves"
        if self._board.can_claim_threefold_repetition():
            return "threefold_repetition"
        return None

    @property
    def status(self) -> GameStatus:
        """Detailed categorization of game status."""
        if self._clock.timed_out_color is not None:
            return "timeout"
        if self._board.is_checkmate():
            return "checkmate"
        if self._board.is_stalemate():
            return "stalemate"
        if self._board.is_insufficient_material():
            return "draw_insufficient_material"
        if self._board.is_seventyfive_moves():
            return "draw_75_moves"
        if self._board.is_fivefold_repetition():
            return "draw_fivefold_repetition"
        if self._draw_claimed:
            return self._claimed_draw_reason or "draw_claimed"
        return "active"

    @property
    def result(self) -> GameResult:
        """Official FIDE-style game outcome."""
        if self._clock.timed_out_color is not None:
            # FIDE Article 6.9: If opponent lacks mating material, timeout results in a draw.
            if self._clock.timed_out_color == "white":
                return "1/2-1/2" if self._board.has_insufficient_material(chess.BLACK) else "0-1"
            else:
                return "1/2-1/2" if self._board.has_insufficient_material(chess.WHITE) else "1-0"
        if self._board.is_checkmate():
            # If current turn is white, White is checkmated -> Black wins (0-1)
            return "0-1" if self._board.turn == chess.WHITE else "1-0"
        if (
            self._board.is_stalemate()
            or self._board.is_insufficient_material()
            or self._board.is_seventyfive_moves()
            or self._board.is_fivefold_repetition()
            or self._draw_claimed
        ):
            return "1/2-1/2"
        return "*"

    def get_legal_moves_uci(self) -> List[str]:
        """Returns all legal moves in UCI notation (e.g. ['e2e4', 'g1f3'])."""
        return [move.uci() for move in self._board.legal_moves]

    def get_legal_moves_san(self) -> List[str]:
        """Returns all legal moves in SAN notation (e.g. ['e4', 'Nf3'])."""
        return [self._board.san(move) for move in self._board.legal_moves]

    def parse_move(self, move_str: str) -> chess.Move:
        """
        Parses and validates a move string in either UCI or SAN notation.
        
        Args:
            move_str: Move in UCI (e.g. 'e2e4', 'e7e8q') or SAN (e.g. 'e4', 'Nf3', 'O-O').
            
        Returns:
            Validated legal chess.Move object.
            
        Raises:
            IllegalMoveError: If the move cannot be parsed or is illegal in the current position.
        """
        if not move_str or not isinstance(move_str, str):
            raise IllegalMoveError(str(move_str), "Move string must be non-empty.")

        cleaned = move_str.strip()

        # 1. Attempt UCI parsing
        try:
            uci_move = chess.Move.from_uci(cleaned)
            if uci_move in self._board.legal_moves:
                return uci_move
        except ValueError:
            pass

        # 2. Attempt SAN parsing
        try:
            san_move = self._board.parse_san(cleaned)
            if san_move in self._board.legal_moves:
                return san_move
        except (ValueError, chess.IllegalMoveError, chess.AmbiguousMoveError) as err:
            raise IllegalMoveError(cleaned, str(err)) from err

        raise IllegalMoveError(cleaned, "Move is not legal in the current board position.")

    def apply_move(
        self,
        move_str: str,
        expected_version: Optional[int] = None,
        expected_fen: Optional[str] = None,
    ) -> MoveRecord:
        """
        Validates and executes a legal move on the authoritative board.
        
        Args:
            move_str: Move in UCI or SAN notation.
            expected_version: Optional board version counter expected before applying move.
            expected_fen: Optional board FEN string expected before applying move.
            
        Returns:
            MoveRecord containing move details and notation.
            
        Raises:
            GameOverError: If the game has already concluded.
            StalePositionError: If the board version or FEN does not match the expected state.
            IllegalMoveError: If the move is not legal.
        """
        with self._lock:
            # Reconcile clock for active turn before checking game over
            self._clock.update(self.turn)
            if self.is_terminal:
                raise GameOverError(self.status, self.result)

            # Atomic stale-position verification
            if expected_version is not None and self._version != expected_version:
                raise StalePositionError(expected_fen or "", self._board.fen())
            if expected_fen is not None and self._board.fen() != expected_fen:
                raise StalePositionError(expected_fen, self._board.fen())

            move = self.parse_move(move_str)

            # Pre-move attributes for record
            san = self._board.san(move)
            uci = move.uci()
            from_square = chess.square_name(move.from_square)
            to_square = chess.square_name(move.to_square)
            promotion = chess.piece_symbol(move.promotion) if move.promotion else None
            is_capture = self._board.is_capture(move)
            ply = len(self._move_records) + 1

            # Execute on authoritative board
            self._board.push(move)
            self._fen_history.append(self._board.fen())
            self._version += 1

            # Post-move clock transition & snapshot
            self._clock.on_move_executed()
            self._clock.record_snapshot()

            # Post-move check status
            is_check = self._board.is_check()

            record = MoveRecord(
                san=san,
                uci=uci,
                from_square=from_square,
                to_square=to_square,
                promotion=promotion,
                is_capture=is_capture,
                is_check=is_check,
                ply=ply,
            )
            self._move_records.append(record)
            return record

    def undo(self, plies: int = 1) -> List[MoveRecord]:
        """
        Reverts the specified number of plies from the game history.
        
        Args:
            plies: Number of half-moves to undo (default 1).
            
        Returns:
            List of undone MoveRecord objects in order of undoing.
            
        Raises:
            UndoError: If requested plies exceed available history.
        """
        if plies < 1:
            raise ValueError(f"Plies must be >= 1, got {plies}")

        with self._lock:
            available = len(self._move_records)
            if plies > available:
                raise UndoError(requested_plies=plies, available_plies=available)

            undone: List[MoveRecord] = []
            for _ in range(plies):
                self._board.pop()
                record = self._move_records.pop()
                self._fen_history.pop()
                undone.append(record)

            self._draw_claimed = False
            self._claimed_draw_reason = None
            self._clock.undo(plies)
            self._version += 1
            return undone

    def restart(self) -> None:
        """Resets the board to the initial starting position and clears history."""
        with self._lock:
            self._board = chess.Board(self._initial_fen)
            self._move_records.clear()
            self._fen_history = [self._board.fen()]
            self._draw_claimed = False
            self._claimed_draw_reason = None
            self._clock.reset()
            self._version += 1

    def set_fen(self, fen: str) -> None:
        """
        Overwrites the current position with a new valid FEN and resets history.
        
        Args:
            fen: Valid FEN string.
            
        Raises:
            InvalidFENError: If the FEN string is invalid or malformed.
        """
        try:
            new_board = chess.Board(fen)
        except ValueError as err:
            raise InvalidFENError(fen, str(err)) from err

        with self._lock:
            self._board = new_board
            self._initial_fen = fen
            self._move_records.clear()
            self._fen_history = [self._board.fen()]
            self._draw_claimed = False
            self._claimed_draw_reason = None
            self._clock.reset()
            self._version += 1

    def claim_draw(self) -> str:
        """
        Claims a draw if eligible by 50-move rule or threefold repetition.
        
        Returns:
            The reason for the claimed draw ('draw_50_moves' or 'draw_repetition').
            
        Raises:
            GameOverError: If the game has already concluded.
            IllegalMoveError: If no draw can be claimed in the current position.
        """
        with self._lock:
            if self.is_terminal:
                raise GameOverError(self.status, self.result)
            if self._board.can_claim_fifty_moves():
                reason = "draw_50_moves"
            elif self._board.can_claim_threefold_repetition():
                reason = "draw_repetition"
            else:
                raise IllegalMoveError("claim_draw", "No draw can be claimed in the current position.")

            self._draw_claimed = True
            self._claimed_draw_reason = reason
            self._version += 1
            return reason

    def ai_move(self) -> MoveRecord:
        """
        Calculates and applies the optimal move using the custom chess engine
        configured to the active difficulty level.
        
        Guarantees:
        - Captures authoritative position identity (version and FEN) under lock.
        - Limits search time according to computer's remaining clock time.
        - Deducts AI thinking time from computer's clock.
        - Runs search unlocked on a copied board.
        - Atomically verifies position consistency before applying the calculated move.
        - Raises StalePositionError if position changed during search.
        
        Returns:
            MoveRecord of the applied move.
            
        Raises:
            GameOverError: If the game has already concluded or AI times out.
            StalePositionError: If the board changed while search was in progress.
        """
        with self._lock:
            self._clock.update(self.turn)
            if self.is_terminal:
                raise GameOverError(self.status, self.result)
            ai_color: Color = self.turn
            board_copy = self._board.copy()
            expected_fen = self._board.fen()
            expected_version = self._version
            diff = self._difficulty

            search_cfg: Optional[SearchConfig] = None
            skip_search = False
            if self._clock.is_timed:
                rem_seconds = self._clock.white_time if ai_color == "white" else self._clock.black_time
                if rem_seconds is not None:
                    if rem_seconds <= 0.0:
                        raise GameOverError(self.status, self.result)
                    profile = get_difficulty_profile(diff)
                    # Safety margin (20ms) reserved for post-search overhead
                    ai_safety_margin_s = 0.020
                    # Minimum time required to run adversarial search
                    ai_min_search_time_s = 0.010

                    available_search_time = rem_seconds - ai_safety_margin_s
                    if available_search_time < ai_min_search_time_s:
                        # Insufficient time to run search without risking clock expiration;
                        # safely select an immediate legal move in microseconds
                        skip_search = True
                    else:
                        # Strictly bounded by profile and available time minus safety margin;
                        # guarantee search never receives more time than computer has remaining
                        budget_seconds = min(profile.max_time_ms / 1000.0, available_search_time)
                        budget_seconds = min(budget_seconds, rem_seconds)
                        search_cfg = SearchConfig(
                            depth=profile.search_config.depth,
                            algorithm=profile.search_config.algorithm,
                            use_iterative_deepening=profile.search_config.use_iterative_deepening,
                            time_limit_ms=budget_seconds * 1000.0,
                            max_nodes=profile.search_config.max_nodes,
                            use_move_ordering=profile.search_config.use_move_ordering,
                            use_quiescence=profile.search_config.use_quiescence,
                            max_quiescence_depth=profile.search_config.max_quiescence_depth,
                            max_check_depth=profile.search_config.max_check_depth,
                            use_transposition_table=profile.search_config.use_transposition_table,
                            transposition_table_size_mb=profile.search_config.transposition_table_size_mb,
                        )

            start_t = self._clock._time_source()

        if skip_search:
            legal = list(board_copy.legal_moves)
            if not legal:
                raise GameOverError(self.status, self.result)
            move = legal[0]
        else:
            search_res = choose_move(board_copy, config=search_cfg, difficulty=diff)
            if search_res.best_move is None:
                legal = list(board_copy.legal_moves)
                if not legal:
                    raise GameOverError(self.status, self.result)
                move = legal[0]
            else:
                move = search_res.best_move

        elapsed_thinking = self._clock._time_source() - start_t

        with self._lock:
            # Deduct elapsed AI thinking time under lock
            self._clock.deduct_time(ai_color, elapsed_thinking)
            if self._clock.timed_out_color is not None or self.is_terminal:
                raise GameOverError(self.status, self.result)

        return self.apply_move(
            move.uci(),
            expected_version=expected_version,
            expected_fen=expected_fen,
        )

    def get_pgn(self) -> str:
        """
        Generates standard PGN text representing the played game to the current position.
        Includes Event, Site, Date, Round, White, Black, Result headers.
        """
        with self._lock:
            board_copy = self._board.copy()
            diff_label = self._difficulty
            res_str = self.result

        import chess.pgn
        import datetime

        pgn_game = chess.pgn.Game.from_board(board_copy)
        pgn_game.headers["Event"] = "ChessAI Match"
        pgn_game.headers["Site"] = "ChessAI Web App"
        pgn_game.headers["Date"] = datetime.date.today().strftime("%Y.%m.%d")
        pgn_game.headers["Round"] = "1"
        pgn_game.headers["White"] = "Player"
        pgn_game.headers["Black"] = f"ChessAI ({diff_label.capitalize()})"
        pgn_game.headers["Result"] = res_str

        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        return str(pgn_game.accept(exporter))

    def get_state(self) -> GameState:
        """Produces a complete, immutable GameState snapshot."""
        with self._lock:
            self._clock.update(self.turn)
            is_term = self.is_terminal

            can_claim = self._board.can_claim_draw() if not is_term else False
            claim_type: Optional[Literal["fifty_moves", "threefold_repetition"]] = None
            if can_claim:
                if self._board.can_claim_fifty_moves():
                    claim_type = "fifty_moves"
                elif self._board.can_claim_threefold_repetition():
                    claim_type = "threefold_repetition"

            active_clock_side: Optional[Color] = None
            if self._clock.is_timed and self._clock.clock_started and not is_term:
                active_clock_side = self.turn

            return GameState(
                session_id=self.session_id,
                fen=self._board.fen(),
                turn=self.turn,
                fullmove_number=self.fullmove_number,
                halfmove_clock=self.halfmove_clock,
                is_check=self.is_check,
                is_terminal=is_term,
                status=self.status,
                result=self.result,
                san_history=[r.san for r in self._move_records],
                uci_history=[r.uci for r in self._move_records],
                fen_history=list(self._fen_history),
                legal_moves_uci=self.get_legal_moves_uci(),
                legal_moves_san=self.get_legal_moves_san(),
                can_undo=len(self._move_records) > 0,
                difficulty=self._difficulty,
                can_claim_draw=can_claim,
                claimable_draw=claim_type,
                time_control=self._clock.time_control,
                is_timed=self._clock.is_timed,
                white_time_remaining=self._clock.white_time,
                black_time_remaining=self._clock.black_time,
                clock_started=self._clock.clock_started,
                active_clock=active_clock_side,
            )
