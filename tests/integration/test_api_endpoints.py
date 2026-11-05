"""Integration tests for FastAPI REST API endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_session_manager
from backend.game.session import SessionManager
from backend.main import app


@pytest.fixture
def client() -> TestClient:
    """Provides a fresh TestClient with an isolated SessionManager per test."""
    manager = SessionManager()
    app.dependency_overrides[get_session_manager] = lambda: manager
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestSystemEndpoints:
    """Test health and root documentation endpoints."""

    def test_health_check(self, client: TestClient) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_root_metadata(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Chess AI API"
        assert "/docs" in data["docs"]


class TestNewGameEndpoint:
    """Test POST /api/game/new."""

    def test_create_default_game(self, client: TestClient) -> None:
        response = client.post("/api/game/new", json={})
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert data["turn"] == "white"
        assert data["status"] == "active"
        assert data["is_terminal"] is False
        assert len(data["legal_moves_uci"]) == 20

    def test_create_game_with_custom_fen(self, client: TestClient) -> None:
        fen = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        response = client.post("/api/game/new", json={"initial_fen": fen})
        assert response.status_code == 201
        data = response.json()
        assert data["fen"] == fen
        assert data["fullmove_number"] == 2

    def test_create_game_with_invalid_fen_returns_400(self, client: TestClient) -> None:
        response = client.post("/api/game/new", json={"initial_fen": "bad-fen-string"})
        assert response.status_code == 400
        assert "Invalid FEN" in response.json()["detail"]


class TestMakeMoveEndpoint:
    """Test POST /api/game/move."""

    def test_make_legal_moves_in_san_and_uci(self, client: TestClient) -> None:
        create_res = client.post("/api/game/new", json={})
        session_id = create_res.json()["session_id"]

        # Move 1: White plays e4 (SAN)
        res1 = client.post("/api/game/move", json={"session_id": session_id, "move": "e4"})
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["turn"] == "black"
        assert data1["san_history"] == ["e4"]
        assert data1["uci_history"] == ["e2e4"]

        # Move 2: Black plays e7e5 (UCI)
        res2 = client.post("/api/game/move", json={"session_id": session_id, "move": "e7e5"})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["turn"] == "white"
        assert data2["san_history"] == ["e4", "e5"]
        assert data2["uci_history"] == ["e2e4", "e7e5"]

    def test_make_illegal_move_returns_400(self, client: TestClient) -> None:
        create_res = client.post("/api/game/new", json={})
        session_id = create_res.json()["session_id"]

        response = client.post("/api/game/move", json={"session_id": session_id, "move": "e2e5"})
        assert response.status_code == 400
        assert "Invalid move" in response.json()["detail"]

    def test_make_move_unknown_session_returns_404(self, client: TestClient) -> None:
        response = client.post("/api/game/move", json={"session_id": "missing-session", "move": "e4"})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_make_move_after_checkmate_returns_409(self, client: TestClient) -> None:
        create_res = client.post("/api/game/new", json={})
        session_id = create_res.json()["session_id"]

        # Fool's mate: 1. f3 e5 2. g4 Qh4#
        client.post("/api/game/move", json={"session_id": session_id, "move": "f3"})
        client.post("/api/game/move", json={"session_id": session_id, "move": "e5"})
        client.post("/api/game/move", json={"session_id": session_id, "move": "g4"})
        mate_res = client.post("/api/game/move", json={"session_id": session_id, "move": "Qh4#"})
        assert mate_res.status_code == 200
        assert mate_res.json()["status"] == "checkmate"

        # Subsequent move must be rejected with 409 Conflict
        subsequent = client.post("/api/game/move", json={"session_id": session_id, "move": "h3"})
        assert subsequent.status_code == 409
        assert "already over" in subsequent.json()["detail"]


class TestUndoAndRestartEndpoints:
    """Test POST /api/game/undo and POST /api/game/restart."""

    def test_undo_move(self, client: TestClient) -> None:
        create_res = client.post("/api/game/new", json={})
        session_id = create_res.json()["session_id"]

        client.post("/api/game/move", json={"session_id": session_id, "move": "e4"})
        client.post("/api/game/move", json={"session_id": session_id, "move": "e5"})

        undo_res = client.post("/api/game/undo", json={"session_id": session_id, "plies": 1})
        assert undo_res.status_code == 200
        data = undo_res.json()
        assert data["san_history"] == ["e4"]
        assert data["turn"] == "black"

    def test_undo_excessive_plies_returns_400(self, client: TestClient) -> None:
        create_res = client.post("/api/game/new", json={})
        session_id = create_res.json()["session_id"]

        client.post("/api/game/move", json={"session_id": session_id, "move": "e4"})

        undo_res = client.post("/api/game/undo", json={"session_id": session_id, "plies": 2})
        assert undo_res.status_code == 400
        assert "Cannot undo 2 plies" in undo_res.json()["detail"]

    def test_restart_game(self, client: TestClient) -> None:
        create_res = client.post("/api/game/new", json={})
        session_id = create_res.json()["session_id"]

        client.post("/api/game/move", json={"session_id": session_id, "move": "e4"})
        client.post("/api/game/move", json={"session_id": session_id, "move": "e5"})

        restart_res = client.post("/api/game/restart", json={"session_id": session_id})
        assert restart_res.status_code == 200
        data = restart_res.json()
        assert data["san_history"] == []
        assert data["turn"] == "white"
        assert data["can_undo"] is False


class TestGetGameStateEndpoint:
    """Test GET /api/game/state."""

    def test_get_state_existing_session(self, client: TestClient) -> None:
        create_res = client.post("/api/game/new", json={})
        session_id = create_res.json()["session_id"]

        client.post("/api/game/move", json={"session_id": session_id, "move": "Nf3"})

        state_res = client.get(f"/api/game/state?session_id={session_id}")
        assert state_res.status_code == 200
        data = state_res.json()
        assert data["san_history"] == ["Nf3"]
        assert data["turn"] == "black"

    def test_get_state_unknown_session_returns_404(self, client: TestClient) -> None:
        state_res = client.get("/api/game/state?session_id=missing-id")
        assert state_res.status_code == 404


class TestSessionIsolationViaAPI:
    """Verify independent game sessions maintain strict state isolation across REST calls."""

    def test_two_sessions_do_not_interfere(self, client: TestClient) -> None:
        res_a = client.post("/api/game/new", json={})
        sid_a = res_a.json()["session_id"]

        res_b = client.post("/api/game/new", json={})
        sid_b = res_b.json()["session_id"]
        assert sid_a != sid_b

        # Play in session A
        client.post("/api/game/move", json={"session_id": sid_a, "move": "e4"})

        # Check session B is pristine
        state_b = client.get(f"/api/game/state?session_id={sid_b}").json()
        assert state_b["san_history"] == []
        assert state_b["turn"] == "white"

        # Play in session B
        client.post("/api/game/move", json={"session_id": sid_b, "move": "d4"})

        # Re-check session A still has only e4
        state_a = client.get(f"/api/game/state?session_id={sid_a}").json()
        assert state_a["san_history"] == ["e4"]
        assert state_a["turn"] == "black"


class TestDifficultyAndAIMoveEndpoints:
    """Tests difficulty configuration endpoints and automated AI move generation."""

    @pytest.mark.parametrize("diff", ["beginner", "easy", "medium", "hard", "expert"])
    def test_create_game_with_all_five_difficulties(self, client: TestClient, diff: str) -> None:
        """Ensures all 5 difficulty levels can be passed at game initialization."""
        response = client.post("/api/game/new", json={"difficulty": diff})
        assert response.status_code == 201
        data = response.json()
        assert data["difficulty"] == diff
        assert data["status"] == "active"

    def test_create_game_with_invalid_difficulty_returns_400(self, client: TestClient) -> None:
        """Unsupported difficulty returns 400 with helpful error detail."""
        response = client.post("/api/game/new", json={"difficulty": "grandmaster"})
        assert response.status_code == 400
        assert "Invalid difficulty" in response.json()["detail"]
        assert "beginner, easy, medium, hard, expert" in response.json()["detail"]

    def test_update_difficulty_endpoint(self, client: TestClient) -> None:
        """POST /api/game/difficulty updates level mid-game without resetting board."""
        res = client.post("/api/game/new", json={"difficulty": "beginner"})
        sid = res.json()["session_id"]
        assert res.json()["difficulty"] == "beginner"

        # Make a move
        client.post("/api/game/move", json={"session_id": sid, "move": "e4"})

        # Change difficulty to expert
        update_res = client.post("/api/game/difficulty", json={"session_id": sid, "difficulty": "expert"})
        assert update_res.status_code == 200
        updated_data = update_res.json()
        assert updated_data["difficulty"] == "expert"
        assert updated_data["san_history"] == ["e4"]
        assert updated_data["turn"] == "black"

    def test_update_difficulty_invalid_level_returns_400(self, client: TestClient) -> None:
        """Invalid difficulty string returns 400 Bad Request."""
        res = client.post("/api/game/new", json={})
        sid = res.json()["session_id"]

        update_res = client.post("/api/game/difficulty", json={"session_id": sid, "difficulty": "insane"})
        assert update_res.status_code == 400
        assert "Invalid difficulty" in update_res.json()["detail"]

    def test_update_difficulty_unknown_session_returns_404(self, client: TestClient) -> None:
        """Non-existent session returns 404."""
        response = client.post("/api/game/difficulty", json={"session_id": "ghost-session", "difficulty": "easy"})
        assert response.status_code == 404

    def test_make_ai_move_endpoint(self, client: TestClient) -> None:
        """POST /api/game/ai-move computes and executes an AI move."""
        res = client.post("/api/game/new", json={"difficulty": "beginner"})
        sid = res.json()["session_id"]

        ai_res = client.post("/api/game/ai-move", json={"session_id": sid})
        assert ai_res.status_code == 200
        data = ai_res.json()
        assert len(data["san_history"]) == 1
        assert data["turn"] == "black"
        assert data["can_undo"] is True

    def test_make_ai_move_unknown_session_returns_404(self, client: TestClient) -> None:
        """Non-existent session returns 404."""
        response = client.post("/api/game/ai-move", json={"session_id": "ghost-session"})
        assert response.status_code == 404

    def test_make_ai_move_on_terminal_game_returns_409(self, client: TestClient) -> None:
        """Attempting an AI move on a concluded game returns 409 Conflict."""
        # Fool's mate setup
        res = client.post("/api/game/new", json={})
        sid = res.json()["session_id"]

        client.post("/api/game/move", json={"session_id": sid, "move": "f3"})
        client.post("/api/game/move", json={"session_id": sid, "move": "e5"})
        client.post("/api/game/move", json={"session_id": sid, "move": "g4"})
        client.post("/api/game/move", json={"session_id": sid, "move": "Qh4#"})

        ai_res = client.post("/api/game/ai-move", json={"session_id": sid})
        assert ai_res.status_code == 409


class TestAnalysisAndPGNEndpoints:
    """Test POST /api/game/analyze and GET /api/game/pgn."""

    def test_analyze_position_by_session_id(self, client: TestClient) -> None:
        new_res = client.post("/api/game/new", json={})
        sid = new_res.json()["session_id"]

        res = client.post("/api/game/analyze", json={"session_id": sid, "depth": 2})
        assert res.status_code == 200
        data = res.json()
        assert "score_cp" in data
        assert "is_mate" in data
        assert data["depth"] >= 1
        assert data["nodes_searched"] > 0
        assert "best_move_uci" in data
        assert "pv_uci" in data
        assert isinstance(data["pv_uci"], list)
        assert isinstance(data["pv_san"], list)

    def test_analyze_position_by_fen(self, client: TestClient) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        res = client.post("/api/game/analyze", json={"fen": fen, "depth": 2})
        assert res.status_code == 200
        data = res.json()
        assert "score_cp" in data
        assert data["depth"] >= 1
        assert data["best_move_uci"] is not None

    def test_analyze_invalid_fen_returns_400(self, client: TestClient) -> None:
        res = client.post("/api/game/analyze", json={"fen": "invalid_fen_string"})
        assert res.status_code == 400

    def test_analyze_missing_params_returns_400(self, client: TestClient) -> None:
        res = client.post("/api/game/analyze", json={})
        assert res.status_code == 400

    def test_analyze_nonexistent_session_returns_404(self, client: TestClient) -> None:
        res = client.post("/api/game/analyze", json={"session_id": "ghost-sid"})
        assert res.status_code == 404

    def test_export_pgn_endpoint(self, client: TestClient) -> None:
        new_res = client.post("/api/game/new", json={})
        sid = new_res.json()["session_id"]
        client.post("/api/game/move", json={"session_id": sid, "move": "e4"})
        client.post("/api/game/move", json={"session_id": sid, "move": "e5"})

        pgn_res = client.get(f"/api/game/pgn?session_id={sid}")
        assert pgn_res.status_code == 200
        data = pgn_res.json()
        assert data["session_id"] == sid
        assert "1. e4 e5" in data["pgn"]
        assert '[Event "ChessAI Match"]' in data["pgn"]

    def test_export_pgn_nonexistent_session_returns_404(self, client: TestClient) -> None:
        res = client.get("/api/game/pgn?session_id=ghost-sid")
        assert res.status_code == 404

    def test_analyze_isolation_does_not_modify_session(self, client: TestClient) -> None:
        """Analysis of an active game must not alter its board, history, stack, or result."""
        new_res = client.post("/api/game/new", json={})
        sid = new_res.json()["session_id"]
        client.post("/api/game/move", json={"session_id": sid, "move": "e4"})
        client.post("/api/game/move", json={"session_id": sid, "move": "e5"})

        state_before = client.get(f"/api/game/state?session_id={sid}").json()

        # Run analysis
        analyze_res = client.post("/api/game/analyze", json={"session_id": sid, "depth": 2})
        assert analyze_res.status_code == 200

        # Verify state is completely unmodified
        state_after = client.get(f"/api/game/state?session_id={sid}").json()
        assert state_after["fen"] == state_before["fen"]
        assert state_after["san_history"] == state_before["san_history"]
        assert state_after["uci_history"] == state_before["uci_history"]
        assert state_after["turn"] == state_before["turn"]
        assert state_after["result"] == state_before["result"]
        assert state_after["can_undo"] == state_before["can_undo"]

    def test_analyze_arbitrary_fen_isolation(self, client: TestClient) -> None:
        """Analyzing an arbitrary FEN leaves active sessions completely untouched."""
        new_res = client.post("/api/game/new", json={})
        sid = new_res.json()["session_id"]
        state_before = client.get(f"/api/game/state?session_id={sid}").json()

        custom_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
        res = client.post("/api/game/analyze", json={"fen": custom_fen, "depth": 2})
        assert res.status_code == 200

        state_after = client.get(f"/api/game/state?session_id={sid}").json()
        assert state_after == state_before

    def test_analyze_terminal_checkmate_and_stalemate(self, client: TestClient) -> None:
        """Terminal positions return exact White-relative scores and empty best move / PV."""
        # 1. White is checkmated (Fool's mate: 1. f3 e5 2. g4 Qh4#) -> exact -30000
        white_mated_fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
        white_mate_res = client.post("/api/game/analyze", json={"fen": white_mated_fen})
        assert white_mate_res.status_code == 200
        wm_data = white_mate_res.json()
        assert wm_data["is_mate"] is True
        assert wm_data["mate_in_plies"] == 0
        assert wm_data["score_cp"] == -30000
        assert wm_data["best_move_uci"] is None
        assert wm_data["best_move_san"] is None
        assert wm_data["pv_uci"] == []
        assert wm_data["pv_san"] == []
        assert wm_data["depth"] == 0
        assert wm_data["nodes_searched"] == 0

        # 2. Black is checkmated (Scholar's mate: 1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#) -> exact +30000
        black_mated_fen = "r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        black_mate_res = client.post("/api/game/analyze", json={"fen": black_mated_fen})
        assert black_mate_res.status_code == 200
        bm_data = black_mate_res.json()
        assert bm_data["is_mate"] is True
        assert bm_data["mate_in_plies"] == 0
        assert bm_data["score_cp"] == 30000
        assert bm_data["best_move_uci"] is None
        assert bm_data["best_move_san"] is None
        assert bm_data["pv_uci"] == []
        assert bm_data["pv_san"] == []
        assert bm_data["depth"] == 0
        assert bm_data["nodes_searched"] == 0

        # 3. Stalemate position -> exact 0 cp
        stalemate_fen = "7k/5K2/6Q1/8/8/8/8/8 b - - 0 1"
        stale_res = client.post("/api/game/analyze", json={"fen": stalemate_fen})
        assert stale_res.status_code == 200
        stale_data = stale_res.json()
        assert stale_data["is_mate"] is False
        assert stale_data["mate_in_plies"] is None
        assert stale_data["score_cp"] == 0
        assert stale_data["best_move_uci"] is None
        assert stale_data["best_move_san"] is None
        assert stale_data["pv_uci"] == []
        assert stale_data["pv_san"] == []
        assert stale_data["depth"] == 0

        # 4a. Other recognized draw: Insufficient material -> exact 0 cp
        insufficient_fen = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
        insuf_res = client.post("/api/game/analyze", json={"fen": insufficient_fen})
        assert insuf_res.status_code == 200
        insuf_data = insuf_res.json()
        assert insuf_data["is_mate"] is False
        assert insuf_data["mate_in_plies"] is None
        assert insuf_data["score_cp"] == 0
        assert insuf_data["is_terminal"] is True
        assert insuf_data["claimable_draw"] is None
        assert insuf_data["best_move_uci"] is None
        assert insuf_data["best_move_san"] is None
        assert insuf_data["pv_uci"] == []
        assert insuf_data["pv_san"] == []

        # 4b. Other recognized automatic draw: 75-move rule -> exact 0 cp and terminal
        seventyfive_move_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 150 75"
        sf_res = client.post("/api/game/analyze", json={"fen": seventyfive_move_fen})
        assert sf_res.status_code == 200
        sf_data = sf_res.json()
        assert sf_data["is_mate"] is False
        assert sf_data["mate_in_plies"] is None
        assert sf_data["score_cp"] == 0
        assert sf_data["is_terminal"] is True
        assert sf_data["claimable_draw"] is None
        assert sf_data["best_move_uci"] is None
        assert sf_data["pv_uci"] == []

        # 4c. Claimed draw on active session: once claimed, position is terminal
        new_res = client.post("/api/game/new", json={})
        sid = new_res.json()["session_id"]
        rep_moves = ["Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8"]
        for m in rep_moves:
            client.post("/api/game/move", json={"session_id": sid, "move": m})
        claim_res = client.post("/api/game/claim-draw", json={"session_id": sid})
        assert claim_res.status_code == 200
        assert claim_res.json()["is_terminal"] is True
        assert claim_res.json()["status"] == "draw_repetition"

        rep_res = client.post("/api/game/analyze", json={"session_id": sid})
        assert rep_res.status_code == 200
        rep_data = rep_res.json()
        assert rep_data["is_mate"] is False
        assert rep_data["mate_in_plies"] is None
        assert rep_data["score_cp"] == 0
        assert rep_data["is_terminal"] is True
        assert rep_data["best_move_uci"] is None
        assert rep_data["pv_uci"] == []

    def test_analyze_difficulty_respect(self, client: TestClient) -> None:
        """Analysis respects configured difficulty settings."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        res = client.post("/api/game/analyze", json={"fen": fen, "difficulty": "beginner"})
        assert res.status_code == 200
        data = res.json()
        assert data["depth"] == 1
        assert data["tt_stores"] == 0  # Beginner has TT disabled

    def test_concurrent_analysis_requests_on_same_session(self, client: TestClient) -> None:
        """Concurrent analysis requests targeting the same session execute safely without race conditions."""
        import concurrent.futures

        new_res = client.post("/api/game/new", json={})
        sid = new_res.json()["session_id"]
        client.post("/api/game/move", json={"session_id": sid, "move": "e4"})

        def run_req():
            return client.post("/api/game/analyze", json={"session_id": sid, "depth": 2})

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_req) for _ in range(4)]
            results = [f.result() for f in futures]

        for r in results:
            assert r.status_code == 200
            assert "score_cp" in r.json()

        # Session state is intact
        state = client.get(f"/api/game/state?session_id={sid}").json()
        assert state["san_history"] == ["e4"]

    def test_pgn_roundtrip_reconstruction(self, client: TestClient) -> None:
        """Exported PGN replayed by python-chess exactly reconstructs the session position."""
        import io
        import chess
        import chess.pgn

        new_res = client.post("/api/game/new", json={})
        sid = new_res.json()["session_id"]
        moves = ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"]
        for m in moves:
            client.post("/api/game/move", json={"session_id": sid, "move": m})

        final_fen = client.get(f"/api/game/state?session_id={sid}").json()["fen"]

        pgn_res = client.get(f"/api/game/pgn?session_id={sid}")
        assert pgn_res.status_code == 200
        pgn_text = pgn_res.json()["pgn"]

        parsed_game = chess.pgn.read_game(io.StringIO(pgn_text))
        assert parsed_game is not None
        reconstructed_board = parsed_game.board()
        for mv in parsed_game.mainline_moves():
            reconstructed_board.push(mv)

        assert reconstructed_board.fen() == final_fen

    def test_mate_score_conversions_both_sides(self, client: TestClient) -> None:
        """Mate in 1 for White and Mate in 1 for Black are correctly converted with opposite signs."""
        # White to move, mate in 1: 1. Qh7# (e.g. White Q on d3, B on c2, Black K on h8)
        # 7k/6pp/8/8/8/3Q4/2B5/7K w - - 0 1 -> 1. Qxh7# or 1. Qd8#
        white_m1_fen = "7k/6pp/8/8/8/3Q4/2B5/7K w - - 0 1"
        res_w = client.post("/api/game/analyze", json={"fen": white_m1_fen, "depth": 2})
        assert res_w.status_code == 200
        data_w = res_w.json()
        assert data_w["is_mate"] is True
        assert data_w["mate_in_plies"] == 1
        assert data_w["score_cp"] > 29000

        # Black to move, mate in 1: 1... Qh2#
        # 7k/2b5/3q4/8/8/8/6PP/7K b - - 0 1
        black_m1_fen = "7k/2b5/3q4/8/8/8/6PP/7K b - - 0 1"
        res_b = client.post("/api/game/analyze", json={"fen": black_m1_fen, "depth": 2})
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["is_mate"] is True
        assert data_b["mate_in_plies"] == 1
        assert data_b["score_cp"] < -29000

    def test_claim_draw_endpoint_flow(self, client: TestClient) -> None:
        """Test POST /api/game/claim-draw for 400 on unclaimable, 404 on missing, and 200 on eligible repetition."""
        # 1. 404 on unknown session
        res_404 = client.post("/api/game/claim-draw", json={"session_id": "nonexistent-sess"})
        assert res_404.status_code == 404

        # 2. 400 on active game with no repetition / 50-move
        new_res = client.post("/api/game/new", json={})
        sid = new_res.json()["session_id"]
        res_400 = client.post("/api/game/claim-draw", json={"session_id": sid})
        assert res_400.status_code == 400
        assert "no draw can be claimed" in res_400.json()["detail"].lower()

        # 3. Play threefold repetition moves
        rep_moves = ["Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8"]
        for m in rep_moves:
            client.post("/api/game/move", json={"session_id": sid, "move": m})

        # State confirms claim is available
        state_rep = client.get(f"/api/game/state?session_id={sid}").json()
        assert state_rep["can_claim_draw"] is True
        assert state_rep["claimable_draw"] == "threefold_repetition"
        assert state_rep["is_terminal"] is False
        assert state_rep["status"] == "active"

        # Claim the draw via POST /api/game/claim-draw
        claim_res = client.post("/api/game/claim-draw", json={"session_id": sid})
        assert claim_res.status_code == 200
        claim_data = claim_res.json()
        assert claim_data["is_terminal"] is True
        assert claim_data["status"] == "draw_repetition"
        assert claim_data["result"] == "1/2-1/2"

        # Further moves rejected because game is terminal (409 Conflict on GameOverError)
        post_move = client.post("/api/game/move", json={"session_id": sid, "move": "e4"})
        assert post_move.status_code == 409

    def test_claimable_draw_analysis_preserves_search_and_pv(self, client: TestClient) -> None:
        """Positions eligible for draw claim are not suppressed as terminal; engine continues to recommend moves."""
        # 1. 50-move rule eligible FEN
        fm_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 100 50"
        fm_res = client.post("/api/game/analyze", json={"fen": fm_fen, "depth": 2})
        assert fm_res.status_code == 200
        fm_data = fm_res.json()
        assert fm_data["is_terminal"] is False
        assert fm_data["claimable_draw"] == "fifty_moves"
        assert fm_data["best_move_uci"] is not None
        assert len(fm_data["pv_uci"]) > 0

        # 2. Threefold repetition on active session (unclaimed)
        new_res = client.post("/api/game/new", json={})
        sid = new_res.json()["session_id"]
        rep_moves = ["Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8"]
        for m in rep_moves:
            client.post("/api/game/move", json={"session_id": sid, "move": m})

        rep_res = client.post("/api/game/analyze", json={"session_id": sid, "depth": 2})
        assert rep_res.status_code == 200
        rep_data = rep_res.json()
        assert rep_data["is_terminal"] is False
        assert rep_data["claimable_draw"] == "threefold_repetition"
        assert rep_data["best_move_uci"] is not None
        assert len(rep_data["pv_uci"]) > 0

    def test_ai_move_returns_409_conflict_on_stale_position(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When AI move encounters a position modified during calculation, HTTP 409 Conflict is returned."""
        import chess
        from engine.types import SearchResult

        new_res = client.post("/api/game/new", json={})
        sid = new_res.json()["session_id"]

        def fake_search_mutating(board: chess.Board, *args, **kwargs) -> SearchResult:
            # While AI is calculating, human makes a move on the same session
            client.post("/api/game/move", json={"session_id": sid, "move": "e4"})
            move = chess.Move.from_uci("g1f3")
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

        monkeypatch.setattr("backend.game.service.choose_move", fake_search_mutating)

        ai_res = client.post("/api/game/ai-move", json={"session_id": sid})
        assert ai_res.status_code == 409
        detail = ai_res.json()["detail"]
        assert "board position changed during calculation" in detail.lower()



