"""Integration tests for full chess game play-throughs and complex state flows."""

import pytest
from backend.game.session import SessionManager


class TestCompleteGameFlows:
    """Integration scenarios testing full game flows and branching state."""

    def test_scholars_mate_flow(self) -> None:
        """Scholar's Mate: 1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#."""
        manager = SessionManager()
        manager.create_session(session_id="scholars-mate")

        moves = ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#"]
        for move in moves[:-1]:
            state = manager.make_move("scholars-mate", move)
            assert state.status == "active"
            assert not state.is_terminal

        final_state = manager.make_move("scholars-mate", moves[-1])
        assert final_state.is_check
        assert final_state.is_terminal
        assert final_state.status == "checkmate"
        assert final_state.result == "1-0"
        assert final_state.san_history == moves

    def test_undo_and_branch_alternative_line(self) -> None:
        """Test playing a sequence, undoing several plies, and exploring a new line."""
        manager = SessionManager()
        manager.create_session(session_id="branching-game")

        # Initial moves: 1. e4 e5 2. Nf3 Nc6 3. Bc4
        manager.make_move("branching-game", "e4")
        manager.make_move("branching-game", "e5")
        manager.make_move("branching-game", "Nf3")
        manager.make_move("branching-game", "Nc6")
        manager.make_move("branching-game", "Bc4")  # Italian Game

        state_before_undo = manager.get_state("branching-game")
        assert len(state_before_undo.san_history) == 5

        # Undo 3 plies: undo Bc4, Nc6, Nf3 -> only e4, e5 remain
        manager.undo_move("branching-game", plies=3)
        state_after_undo = manager.get_state("branching-game")
        assert state_after_undo.san_history == ["e4", "e5"]
        assert state_after_undo.turn == "white"

        # Play an alternative continuation: 2. d4 (Center Game)
        manager.make_move("branching-game", "d4")
        branch_state = manager.get_state("branching-game")
        assert branch_state.san_history == ["e4", "e5", "d4"]
        assert branch_state.turn == "black"

    def test_promotion_delivering_check_integration(self) -> None:
        """Test pawn advancing and promoting to Knight to deliver check."""
        # FEN with White pawn on f7, Black king on g6. Knight promotion to f8 delivers check!
        fen = "4K3/5P2/6k1/8/8/8/8/8 w - - 0 1"
        manager = SessionManager()
        manager.create_session(session_id="promo-flow", initial_fen=fen)

        # Promote to Knight: f7f8n -> f8=N+
        state = manager.make_move("promo-flow", "f7f8n")
        assert state.is_check
        assert state.san_history[-1] == "f8=N+"
        assert state.turn == "black"

    def test_draw_by_repetition_flow(self) -> None:
        """Test threefold repetition integration flow via session manager: claimable then claimed."""
        manager = SessionManager()
        manager.create_session(session_id="rep-flow")

        repetition_moves = [
            "Nf3", "Nf6", "Ng1", "Ng8",
            "Nf3", "Nf6", "Ng1", "Ng8",
        ]
        for m in repetition_moves:
            state = manager.make_move("rep-flow", m)

        # Repetition reached: claimable, not automatically terminal
        assert not state.is_terminal
        assert state.can_claim_draw is True
        assert state.claimable_draw == "threefold_repetition"
        assert state.status == "active"
        assert state.result == "*"

        # Player claims the draw
        claimed_state = manager.claim_draw("rep-flow")
        assert claimed_state.is_terminal
        assert claimed_state.status == "draw_repetition"
        assert claimed_state.result == "1/2-1/2"
