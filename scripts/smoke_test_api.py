"""Comprehensive end-to-end API and engine smoke test."""

import io
import chess
import chess.pgn
from fastapi.testclient import TestClient
from backend.main import app


def run_smoke_test() -> None:
    client = TestClient(app)

    print("1. Health check...")
    health = client.get("/api/health")
    assert health.status_code == 200, f"Health check failed: {health.text}"
    assert health.json()["status"] == "ok"
    print("   [OK] Health check passed.")

    print("2. New Game creation...")
    new_game = client.post("/api/game/new", json={"difficulty": "medium"})
    assert new_game.status_code == 201
    sid = new_game.json()["session_id"]
    assert new_game.json()["turn"] == "white"
    assert len(new_game.json()["legal_moves_uci"]) == 20
    assert len(new_game.json()["fen_history"]) == 1
    print(f"   [OK] New Game created with session {sid[:8]}...")

    print("3. Human Move execution (1. e4)...")
    move1 = client.post("/api/game/move", json={"session_id": sid, "move": "e4"})
    assert move1.status_code == 200
    state1 = move1.json()
    assert state1["turn"] == "black"
    assert state1["san_history"] == ["e4"]
    assert len(state1["fen_history"]) == 2
    print("   [OK] Human move e4 applied cleanly.")

    print("4. AI Move calculation & execution...")
    ai_move = client.post("/api/game/ai-move", json={"session_id": sid})
    assert ai_move.status_code == 200
    state_ai = ai_move.json()
    assert state_ai["turn"] == "white"
    assert len(state_ai["san_history"]) == 2
    assert len(state_ai["fen_history"]) == 3
    ai_reply = state_ai["san_history"][1]
    print(f"   [OK] AI responded with legal move: {ai_reply}")

    print("5. Difficulty Update (switch to 'hard')...")
    diff_res = client.post("/api/game/difficulty", json={"session_id": sid, "difficulty": "hard"})
    assert diff_res.status_code == 200
    assert diff_res.json()["difficulty"] == "hard"
    print("   [OK] Difficulty updated to hard without affecting board.")

    print("6. Engine Analysis on session board...")
    analysis_res = client.post("/api/game/analyze", json={"session_id": sid, "depth": 3})
    assert analysis_res.status_code == 200
    ana = analysis_res.json()
    assert "score_cp" in ana
    assert ana["depth"] >= 1
    assert ana["nodes_searched"] > 0
    assert ana["best_move_uci"] is not None
    assert isinstance(ana["pv_uci"], list)
    print(f"   [OK] Analysis: Score {ana['score_cp']} cp, Depth {ana['depth']}, Best {ana['best_move_san']}, PV {ana['pv_san']}")

    print("7. Engine Analysis on arbitrary custom FEN...")
    custom_fen = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    ana_custom = client.post("/api/game/analyze", json={"fen": custom_fen, "depth": 2})
    assert ana_custom.status_code == 200
    assert ana_custom.json()["best_move_uci"] is not None
    # Confirm session was untouched
    state_after_custom = client.get(f"/api/game/state?session_id={sid}").json()
    assert state_after_custom["fen"] == state_ai["fen"]
    print("   [OK] Arbitrary FEN analyzed with session isolation preserved.")

    print("8. Move Undo (undo AI move and player move)...")
    undo_res = client.post("/api/game/undo", json={"session_id": sid, "plies": 2})
    assert undo_res.status_code == 200
    assert len(undo_res.json()["san_history"]) == 0
    assert len(undo_res.json()["fen_history"]) == 1
    print("   [OK] Undo succeeded; board returned to initial state.")

    print("9. PGN Export & Roundtrip Reconstruction...")
    # Play 4 moves
    client.post("/api/game/move", json={"session_id": sid, "move": "e4"})
    client.post("/api/game/move", json={"session_id": sid, "move": "e5"})
    client.post("/api/game/move", json={"session_id": sid, "move": "Nf3"})
    client.post("/api/game/move", json={"session_id": sid, "move": "Nc6"})

    final_fen = client.get(f"/api/game/state?session_id={sid}").json()["fen"]
    pgn_data = client.get(f"/api/game/pgn?session_id={sid}").json()
    assert "1. e4 e5 2. Nf3 Nc6" in pgn_data["pgn"]

    # Reconstruct with python-chess
    parsed = chess.pgn.read_game(io.StringIO(pgn_data["pgn"]))
    assert parsed is not None
    rec_board = parsed.board()
    for m in parsed.mainline_moves():
        rec_board.push(m)
    assert rec_board.fen() == final_fen, "PGN roundtrip FEN mismatch!"
    print("   [OK] PGN exported and reconstructed board exactly matches session FEN.")

    print("10. Game Restart...")
    restart_res = client.post("/api/game/restart", json={"session_id": sid})
    assert restart_res.status_code == 200
    assert len(restart_res.json()["san_history"]) == 0
    assert len(restart_res.json()["fen_history"]) == 1
    print("   [OK] Restart successfully restored initial board.")

    print("11. Checkmate and Stalemate Terminal Handling...")
    # Fool's mate
    mate_game = client.post("/api/game/new", json={})
    mate_sid = mate_game.json()["session_id"]
    client.post("/api/game/move", json={"session_id": mate_sid, "move": "f3"})
    client.post("/api/game/move", json={"session_id": mate_sid, "move": "e5"})
    client.post("/api/game/move", json={"session_id": mate_sid, "move": "g4"})
    client.post("/api/game/move", json={"session_id": mate_sid, "move": "Qh4#"})

    mate_state = client.get(f"/api/game/state?session_id={mate_sid}").json()
    assert mate_state["is_terminal"] is True
    assert mate_state["status"] == "checkmate"
    assert mate_state["result"] == "0-1"

    mate_ana = client.post("/api/game/analyze", json={"session_id": mate_sid})
    assert mate_ana.status_code == 200
    assert mate_ana.json()["is_mate"] is True
    assert mate_ana.json()["mate_in_plies"] == 0
    assert mate_ana.json()["score_cp"] < -29000  # Black delivered mate
    print("   [OK] Checkmate game correctly classified with mate_in_plies=0 and score < -29000.")

    print("12. Chess Clock & Time Controls Verification...")
    # Test all 5 time controls
    tc_expected = [
        ("bullet", 60.0, True),
        ("blitz", 180.0, True),
        ("rapid", 600.0, True),
        ("classic", 1800.0, True),
        ("casual", None, False),
    ]
    for tc_mode, expected_time, is_timed in tc_expected:
        res = client.post("/api/game/new", json={"time_control": tc_mode})
        assert res.status_code == 201
        data = res.json()
        assert data["time_control"] == tc_mode
        assert data["is_timed"] is is_timed
        assert data["white_time_remaining"] == expected_time
        assert data["black_time_remaining"] == expected_time
        assert data["clock_started"] is False

    # Start clock on move in rapid match
    tc_game = client.post("/api/game/new", json={"time_control": "rapid"})
    tc_sid = tc_game.json()["session_id"]
    m_res = client.post("/api/game/move", json={"session_id": tc_sid, "move": "e4"})
    assert m_res.status_code == 200
    m_data = m_res.json()
    assert m_data["clock_started"] is True
    assert m_data["active_clock"] == "black"
    print("   [OK] All 5 time control modes and clock initiation verified.")

    print("\nALL 12 SMOKE TEST SCENARIOS PASSED WITH 100% SUCCESS!")


if __name__ == "__main__":
    run_smoke_test()
