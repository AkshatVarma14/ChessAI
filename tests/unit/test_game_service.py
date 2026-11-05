"""Unit tests for the Game service class."""

import pytest
import chess

from backend.game.exceptions import (
    GameOverError,
    IllegalMoveError,
    InvalidFENError,
    StalePositionError,
    UndoError,
)
from backend.game.service import Game
from engine.types import SearchResult


class TestGameInitialization:
    """Test game creation and FEN handling."""

    def test_default_game_initialization(self) -> None:
        game = Game("session-1")
        assert game.session_id == "session-1"
        assert game.fen == chess.STARTING_FEN
        assert game.turn == "white"
        assert game.fullmove_number == 1
        assert game.halfmove_clock == 0
        assert not game.is_check
        assert not game.is_terminal
        assert game.status == "active"
        assert game.result == "*"

    def test_game_board_property(self) -> None:
        game = Game("session-board")
        board_copy = game.board
        assert isinstance(board_copy, chess.Board)
        # Modifying the copy should not affect the internal authoritative board
        board_copy.push_san("e4")
        assert game.fen == chess.STARTING_FEN

    def test_set_fen_valid_and_invalid(self) -> None:
        game = Game("session-set-fen")
        new_fen = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        game.set_fen(new_fen)
        assert game.fen == new_fen

        with pytest.raises(InvalidFENError):
            game.set_fen("garbage-fen")

    def test_empty_or_none_move_raises_illegal_move_error(self) -> None:
        game = Game("session-empty-move")
        with pytest.raises(IllegalMoveError):
            game.apply_move("")
        with pytest.raises(IllegalMoveError):
            game.apply_move("   ")

    def test_custom_valid_fen(self) -> None:
        fen = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        game = Game("session-custom", initial_fen=fen)
        assert game.fen == fen
        assert game.turn == "white"
        assert game.fullmove_number == 2

    def test_invalid_fen_raises_error(self) -> None:
        with pytest.raises(InvalidFENError):
            Game("session-invalid", initial_fen="invalid-fen-string")


class TestMoveExecutionAndNotation:
    """Test playing moves in UCI and SAN, and move record details."""

    def test_apply_move_san_and_uci(self) -> None:
        game = Game("session-notation")
        rec1 = game.apply_move("e4")
        assert rec1.san == "e4"
        assert rec1.uci == "e2e4"
        assert rec1.from_square == "e2"
        assert rec1.to_square == "e4"
        assert not rec1.is_capture
        assert not rec1.is_check
        assert rec1.ply == 1

        rec2 = game.apply_move("e7e5")  # UCI notation
        assert rec2.san == "e5"
        assert rec2.uci == "e7e5"
        assert rec2.ply == 2

    def test_capture_and_check_records(self) -> None:
        # FEN where White can capture with check: White Queen on f5, Black pawn on f7
        fen = "rnbqkbnr/pppppppp/8/5Q2/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1"
        game = Game("session-capture-check", initial_fen=fen)
        record = game.apply_move("Qxf7+")
        assert record.is_capture
        assert record.is_check
        assert record.san == "Qxf7+"


class TestUndoAndRestart:
    """Test undoing moves and restarting the game."""

    def test_undo_single_ply(self) -> None:
        game = Game("session-undo")
        initial_fen = game.fen
        game.apply_move("e4")
        assert game.turn == "black"

        undone = game.undo(1)
        assert len(undone) == 1
        assert undone[0].san == "e4"
        assert game.fen == initial_fen
        assert game.turn == "white"
        assert len(game.get_state().san_history) == 0

    def test_undo_multiple_plies(self) -> None:
        game = Game("session-multi-undo")
        initial_fen = game.fen
        game.apply_move("e4")
        game.apply_move("e5")
        game.apply_move("Nf3")

        undone = game.undo(2)
        assert len(undone) == 2
        # After undoing 2 plies (Nf3 and e5), only e4 remains
        assert game.turn == "black"
        state = game.get_state()
        assert state.san_history == ["e4"]

        # Undo the remaining ply
        game.undo(1)
        assert game.fen == initial_fen
        assert game.turn == "white"

    def test_undo_beyond_history_raises_error(self) -> None:
        game = Game("session-undo-error")
        game.apply_move("e4")
        with pytest.raises(UndoError):
            game.undo(2)

    def test_undo_with_zero_or_negative_plies_raises_value_error(self) -> None:
        game = Game("session-undo-val")
        game.apply_move("e4")
        with pytest.raises(ValueError):
            game.undo(0)

    def test_restart_restores_initial_position(self) -> None:
        game = Game("session-restart")
        initial_fen = game.fen
        game.apply_move("e4")
        game.apply_move("e5")
        game.apply_move("Nf3")
        assert len(game.get_state().san_history) == 3

        game.restart()
        assert game.fen == initial_fen
        assert game.turn == "white"
        assert len(game.get_state().san_history) == 0
        assert not game.get_state().can_undo


class TestSinglePlyUndoSpecifications:
    """Rigorous tests for Stage 10.3 single-ply undo invariants."""

    def test_single_ply_undo_after_human_move(self) -> None:
        """Scenario A: White plays 1. e4; undo reverts 1 ply back to start."""
        game = Game("session-undo-human")
        initial_fen = game.fen
        game.apply_move("e4")
        assert game.turn == "black"
        assert len(game.get_state().san_history) == 1

        undone = game.undo(1)
        assert len(undone) == 1
        assert undone[0].san == "e4"
        assert game.fen == initial_fen
        assert game.turn == "white"
        assert len(game.get_state().san_history) == 0
        assert not game.get_state().can_undo

    def test_single_ply_undo_after_ai_move(self) -> None:
        """Scenario B: White plays 1. e4, AI plays 1... d5; undo reverts only 1... d5."""
        game = Game("session-undo-ai")
        game.apply_move("e4")
        fen_after_e4 = game.fen

        # AI responds with a legal move
        ai_record = game.ai_move()
        assert len(game.get_state().san_history) == 2
        assert game.turn == "white"

        # Single-ply undo reverts only the AI's move
        undone = game.undo(1)
        assert len(undone) == 1
        assert undone[0].uci == ai_record.uci
        assert game.fen == fen_after_e4
        assert game.turn == "black"  # Turn returns to Black (computer)
        assert game.get_state().san_history == ["e4"]
        assert game.get_state().can_undo

    def test_consecutive_single_ply_undos(self) -> None:
        """Two consecutive single-ply undos revert moves one-by-one."""
        game = Game("session-consecutive-undo")
        initial_fen = game.fen
        game.apply_move("e4")
        fen_after_e4 = game.fen
        game.apply_move("d5")

        # First undo removes d5
        undone_1 = game.undo(1)
        assert len(undone_1) == 1
        assert undone_1[0].san == "d5"
        assert game.fen == fen_after_e4
        assert game.turn == "black"
        assert game.get_state().san_history == ["e4"]

        # Second undo removes e4
        undone_2 = game.undo(1)
        assert len(undone_2) == 1
        assert undone_2[0].san == "e4"
        assert game.fen == initial_fen
        assert game.turn == "white"
        assert len(game.get_state().san_history) == 0
        assert not game.get_state().can_undo

    def test_undo_restores_castling_rights(self) -> None:
        """Undoing a king or rook move or castling restores castling rights."""
        # Setup position where White can castle: 1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O
        game = Game("session-castling-undo")
        for m in ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"]:
            game.apply_move(m)

        assert game.board.has_kingside_castling_rights(chess.WHITE)
        fen_before_castle = game.fen

        # White castles
        game.apply_move("O-O")
        assert not game.board.has_kingside_castling_rights(chess.WHITE)
        assert game.board.piece_at(chess.G1) == chess.Piece(chess.KING, chess.WHITE)
        assert game.board.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)

        # Undo castling
        game.undo(1)
        assert game.fen == fen_before_castle
        assert game.board.has_kingside_castling_rights(chess.WHITE)
        assert game.board.piece_at(chess.E1) == chess.Piece(chess.KING, chess.WHITE)
        assert game.board.piece_at(chess.H1) == chess.Piece(chess.ROOK, chess.WHITE)

    def test_undo_restores_en_passant_target(self) -> None:
        """Undoing restores previous en passant target and halfmove clock."""
        game = Game("session-ep-undo")
        game.apply_move("e4")
        # e4 creates en passant target e3
        assert game.board.ep_square == chess.E3
        assert game.board.halfmove_clock == 0

        game.apply_move("Nf6")
        assert game.board.ep_square is None
        assert game.board.halfmove_clock == 1

        game.undo(1)
        assert game.board.ep_square == chess.E3
        assert game.board.halfmove_clock == 0

    def test_undo_after_terminal_checkmate(self) -> None:
        """Undoing checkmate re-opens the game and resets is_terminal."""
        game = Game("session-terminal-undo")
        # Scholar's mate: 1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7#
        for m in ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6"]:
            game.apply_move(m)

        fen_before_mate = game.fen
        game.apply_move("Qxf7#")
        assert game.is_terminal
        assert game.status == "checkmate"
        assert game.result == "1-0"

        # Single-ply undo reverts the checkmating move
        undone = game.undo(1)
        assert len(undone) == 1
        assert undone[0].san == "Qxf7#"
        assert not game.is_terminal
        assert game.status == "active"
        assert game.result == "*"
        assert game.fen == fen_before_mate
        assert game.turn == "white"

    def test_undo_after_claimed_draw_clears_draw_flag(self) -> None:
        """Undoing after a claimed draw clears claimed status and reverts position."""
        # Setup position with threefold repetition
        game = Game("session-draw-undo")
        for m in ["Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8"]:
            game.apply_move(m)

        assert game.can_claim_draw
        reason = game.claim_draw()
        assert reason == "draw_repetition"
        assert game.is_terminal
        assert game.status == "draw_repetition"

        # Undo the last move (Ng8)
        game.undo(1)
        assert not game.is_terminal
        assert game.status == "active"
        assert game.result == "*"
        assert game.turn == "black"

    def test_undo_after_restart_raises_undo_error(self) -> None:
        """Calling undo on a restarted game raises UndoError."""
        game = Game("session-restart-undo")
        game.apply_move("e4")
        game.restart()
        assert not game.get_state().can_undo
        with pytest.raises(UndoError):
            game.undo(1)

    def test_undo_increments_version_protecting_against_stale_ai(self) -> None:
        """Undo increments _version counter, preventing stale AI move application."""
        from backend.game.exceptions import StalePositionError
        game = Game("session-version-protect")
        game.apply_move("e4")
        initial_version = game._version

        # Simulating concurrent search that recorded version before undo
        captured_version = game._version
        captured_fen = game.fen

        # User clicks undo
        game.undo(1)
        assert game._version > initial_version

        # Stale move from earlier position must be rejected
        with pytest.raises(StalePositionError):
            game.apply_move(
                "d5",
                expected_version=captured_version,
                expected_fen=captured_fen,
            )


class TestGameOverRestrictions:
    """Test that moves cannot be played after checkmate."""

    def test_move_after_checkmate_raises_game_over_error(self) -> None:
        game = Game("session-over")
        game.apply_move("f3")
        game.apply_move("e5")
        game.apply_move("g4")
        game.apply_move("Qh4#")
        assert game.is_terminal

        with pytest.raises(GameOverError):
            game.apply_move("e4")


class TestGameStateSnapshot:
    """Test GameState model generation and immutability."""

    def test_game_state_attributes(self) -> None:
        game = Game("session-snapshot")
        game.apply_move("d4")
        game.apply_move("d5")

        state = game.get_state()
        assert state.session_id == "session-snapshot"
        assert state.turn == "white"
        assert state.fullmove_number == 2
        assert state.san_history == ["d4", "d5"]
        assert state.uci_history == ["d2d4", "d7d5"]
        assert len(state.legal_moves_uci) > 0
        assert len(state.legal_moves_san) > 0
        assert state.can_undo is True
        assert state.is_terminal is False
        assert state.difficulty == "medium"


class TestGameDifficultyAndAIMoves:
    """Test engine difficulty integration and automated AI moves."""

    def test_difficulty_initialization_and_validation(self) -> None:
        """Verifies custom difficulty at init and rejection of invalid values."""
        game = Game("session-diff", difficulty="expert")
        assert game.difficulty == "expert"
        assert game.get_state().difficulty == "expert"

        # Invalid difficulty rejected
        with pytest.raises(ValueError, match="Invalid difficulty 'super_hard'"):
            Game("session-bad", difficulty="super_hard")

    def test_set_difficulty_mid_game(self) -> None:
        """Updating difficulty changes active level without resetting board."""
        game = Game("session-change-diff", difficulty="beginner")
        game.apply_move("e4")
        game.set_difficulty("hard")

        assert game.difficulty == "hard"
        assert game.fen != chess.STARTING_FEN
        assert game.get_state().san_history == ["e4"]
        assert game.get_state().difficulty == "hard"

    def test_ai_move_execution(self) -> None:
        """Engine calculates and executes a legal move on the board."""
        game = Game("session-ai", difficulty="beginner")
        assert game.turn == "white"

        move_record = game.ai_move()
        assert move_record.san in [r.san for r in game._move_records]
        assert game.turn == "black"
        assert len(game.get_state().san_history) == 1
        assert game.get_state().can_undo is True

    def test_ai_move_in_terminal_state_raises_game_over(self) -> None:
        """Cannot request an AI move on an already completed game."""
        # Fool's mate position
        game = Game("session-ai-over")
        game.apply_move("f3")
        game.apply_move("e5")
        game.apply_move("g4")
        game.apply_move("Qh4#")
        assert game.is_terminal

        with pytest.raises(GameOverError):
            game.ai_move()

    def test_fen_history_tracking_and_undo(self) -> None:
        """Game service tracks complete FEN history through moves and undos."""
        game = Game("session-fen-history")
        assert len(game.get_state().fen_history) == 1
        assert game.get_state().fen_history[0] == chess.STARTING_FEN

        game.apply_move("e4")
        assert len(game.get_state().fen_history) == 2
        assert game.get_state().fen_history[1] == game.fen

        game.apply_move("e5")
        assert len(game.get_state().fen_history) == 3
        assert game.get_state().fen_history[2] == game.fen

        # Undo 1 ply
        game.undo(1)
        assert len(game.get_state().fen_history) == 2
        assert game.get_state().fen_history[-1] == game.fen

        # Restart
        game.restart()
        assert len(game.get_state().fen_history) == 1
        assert game.get_state().fen_history[0] == chess.STARTING_FEN

    def test_get_pgn_export(self) -> None:
        """Game produces standard PGN representation with headers and moves."""
        game = Game("session-pgn")
        game.apply_move("e4")
        game.apply_move("e5")
        game.apply_move("Nf3")

        pgn_str = game.get_pgn()
        assert "1. e4 e5 2. Nf3" in pgn_str
        assert '[Event "ChessAI Match"]' in pgn_str
        assert '[Site "ChessAI Web App"]' in pgn_str
        assert '[Round "1"]' in pgn_str
        assert '[White "Player"]' in pgn_str
        assert '[Result "*"]' in pgn_str


class TestGameLockAndConcurrency:
    """Rigorous verification of lock correctness, non-recursive acquisition, and thread safety."""

    def test_lock_type_and_non_recursive_acquisition(self) -> None:
        """Lock is a standard threading.Lock and all public methods succeed without recursive deadlock."""
        import threading

        game = Game("session-lock-test")
        # Verify lock is a standard Lock (non-reentrant mutex)
        assert isinstance(game._lock, type(threading.Lock()))

        # Sequential invocations of all locked methods
        state = game.get_state()
        assert state.turn == "white"

        board_copy = game.board
        assert board_copy.fen() == chess.STARTING_FEN

        rec = game.apply_move("e4")
        assert rec.san == "e4"

        pgn_text = game.get_pgn()
        assert "1. e4" in pgn_text

        undone = game.undo(1)
        assert len(undone) == 1

        game.restart()
        assert game.fen == chess.STARTING_FEN

        custom_fen = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        game.set_fen(custom_fen)
        assert game.fen == custom_fen

        # ai_move() releases lock before choose_move() and reacquires via apply_move()
        ai_rec = game.ai_move()
        assert ai_rec is not None
        assert game.turn == "black"

    def test_concurrent_game_operations_with_bounded_timeout(self) -> None:
        """Concurrent threads interacting with Game instance complete safely within bounded timeout."""
        import concurrent.futures

        game = Game("session-concurrent")

        def worker_read():
            _ = game.get_state()
            _ = game.board
            _ = game.get_pgn()
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_read) for _ in range(50)]
            # Bounded timeout of 5.0s prevents any indefinite hanging on deadlock
            for f in futures:
                assert f.result(timeout=5.0) is True

    def test_ai_move_releases_lock_during_engine_search(self) -> None:
        """ai_move releases self._lock before running choose_move so concurrent reads are not blocked."""
        import concurrent.futures
        import time

        # Medium difficulty takes ~100-800ms
        game = Game("session-ai-lock", difficulty="medium")

        lock_acquired_during_search = False

        def run_ai():
            return game.ai_move()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            ai_future = executor.submit(run_ai)

            # Give a brief moment for ai_move to enter search
            time.sleep(0.02)

            # Try to acquire lock and inspect state while ai_move is computing
            start = time.perf_counter()
            with game._lock:
                lock_acquired_during_search = True
                _ = game._board.fen()
            elapsed = time.perf_counter() - start

            # AI move must complete cleanly within 5.0 seconds
            ai_rec = ai_future.result(timeout=5.0)
            assert ai_rec is not None
            assert lock_acquired_during_search is True
            # Acquiring the lock during search was fast (<200ms) rather than waiting for entire AI search
            assert elapsed < 1.0


class TestAIMoveConcurrencyAndStaleProtection:
    """Test stale-position protection and concurrency invariants in Game.ai_move()."""

    @staticmethod
    def _make_dummy_result(move_uci: str) -> SearchResult:
        move = chess.Move.from_uci(move_uci)
        return SearchResult(
            best_move=move,
            best_move_uci=move.uci(),
            best_move_san=move.uci(),
            score_cp=10,
            depth=1,
            nodes_searched=1,
            pruned_nodes=0,
            elapsed_ms=1.0,
            nodes_per_second=1000,
            algorithm="alpha_beta",
        )

    def test_version_increments_on_all_state_mutations(self) -> None:
        """Game._version increments monotonically on moves, undos, resets, FEN changes, and draw claims."""
        game = Game("version-check")
        assert game.version == 0

        game.apply_move("e4")
        assert game.version == 1

        game.undo(1)
        assert game.version == 2

        game.restart()
        assert game.version == 3

        game.set_fen("rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
        assert game.version == 4

        # Set up a claimable draw position
        rep_fen = "r3k3/8/8/8/8/8/8/4K2R w K - 100 50"
        game.set_fen(rep_fen)
        assert game.version == 5
        game.claim_draw()
        assert game.version == 6

    def test_ai_move_rejects_when_human_move_intervenes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If a human move arrives while AI is searching, the stale AI move is safely rejected."""
        game = Game("stale-human")

        def fake_search(board: chess.Board, *args, **kwargs) -> SearchResult:
            # Simulate human move arriving while search is in progress
            game.apply_move("e4")
            return self._make_dummy_result("g1f3")

        monkeypatch.setattr("backend.game.service.choose_move", fake_search)

        with pytest.raises(StalePositionError) as exc_info:
            game.ai_move()

        assert "board position changed during calculation" in str(exc_info.value)
        # Verify board and move history are intact with only the human move
        assert game.get_state().san_history == ["e4"]
        assert game.turn == "black"
        assert game.version == 1

    def test_ai_move_rejects_when_restart_intervenes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If a game restart occurs while AI is searching, the stale AI move is safely rejected."""
        game = Game("stale-restart")
        game.apply_move("e4")

        def fake_search(board: chess.Board, *args, **kwargs) -> SearchResult:
            # Simulate user hitting restart while search is in progress
            game.restart()
            return self._make_dummy_result("e7e5")

        monkeypatch.setattr("backend.game.service.choose_move", fake_search)

        with pytest.raises(StalePositionError):
            game.ai_move()

        assert game.get_state().san_history == []
        assert game.fen == chess.STARTING_FEN
        assert game.turn == "white"

    def test_ai_move_rejects_when_undo_intervenes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If an undo occurs while AI is searching, the stale AI move is safely rejected."""
        game = Game("stale-undo")
        game.apply_move("e4")
        game.apply_move("e5")

        def fake_search(board: chess.Board, *args, **kwargs) -> SearchResult:
            # Simulate undo during search
            game.undo(1)
            return self._make_dummy_result("g1f3")

        monkeypatch.setattr("backend.game.service.choose_move", fake_search)

        with pytest.raises(StalePositionError):
            game.ai_move()

        assert game.get_state().san_history == ["e4"]
        assert game.turn == "black"

    def test_stale_move_is_rejected_even_if_legally_playable_in_newer_position(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stale AI move must be rejected even if the same move happens to be legal in the mutated position."""
        game = Game("stale-legal-overlap")

        def fake_search(board: chess.Board, *args, **kwargs) -> SearchResult:
            # In the starting position, AI decided on Nf3 (g1f3)
            # Meanwhile, human plays 'h3', leaving Nf3 (g1f3) still legally playable!
            game.apply_move("h3")
            return self._make_dummy_result("g1f3")

        monkeypatch.setattr("backend.game.service.choose_move", fake_search)

        # Even though g1f3 might be legal in the new position (or if turn permitted),
        # position consistency check rejects it unconditionally!
        with pytest.raises(StalePositionError):
            game.ai_move()

        assert game.get_state().san_history == ["h3"]
        assert game.turn == "black"

    def test_concurrent_ai_move_requests_atomically_resolve(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When two concurrent AI move requests race for the same position, exactly one succeeds and the other raises StalePositionError."""
        import concurrent.futures
        import threading
        from backend.game.service import choose_move

        game = Game("concurrent-ai-race", difficulty="easy")
        barrier = threading.Barrier(2)
        real_choose = choose_move

        def synchronized_choose(board, *args, **kwargs):
            barrier.wait(timeout=3.0)
            return real_choose(board, *args, **kwargs)

        monkeypatch.setattr("backend.game.service.choose_move", synchronized_choose)

        results = []
        errors = []

        def worker():
            try:
                rec = game.ai_move()
                results.append(rec)
            except StalePositionError as err:
                errors.append(err)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker)
            f2 = executor.submit(worker)
            f1.result(timeout=5.0)
            f2.result(timeout=5.0)

        # Exactly one worker succeeded and applied the move
        assert len(results) == 1
        # The other worker detected the version increment and raised StalePositionError
        assert len(errors) == 1
        # Exactly one move was applied to the board
        assert len(game.get_state().san_history) == 1
        assert game.version == 1


class TestDrawSemanticsInGameService:
    """Test claimable vs automatic draw semantics in Game service."""

    def test_claim_draw_validation(self) -> None:
        """Attempting to claim draw when not eligible raises IllegalMoveError."""
        game = Game("invalid-draw-claim")
        assert game.can_claim_draw is False
        assert game.claimable_draw is None

        with pytest.raises(IllegalMoveError) as exc_info:
            game.claim_draw()
        assert "No draw can be claimed" in str(exc_info.value)

    def test_claim_draw_on_terminal_game_raises_game_over(self) -> None:
        """Attempting to claim draw on an already-terminal game raises GameOverError."""
        # Fool's mate position
        game = Game("terminal-claim")
        game.apply_move("f3")
        game.apply_move("e5")
        game.apply_move("g4")
        game.apply_move("Qh4#")
        assert game.is_terminal

        with pytest.raises(GameOverError):
            game.claim_draw()


