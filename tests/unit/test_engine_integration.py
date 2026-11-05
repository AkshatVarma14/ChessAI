"""Integration tests verifying the engine integrates cleanly with Game service."""

import pytest
import chess

from backend.game.service import Game
from engine import choose_move, SearchConfig, EvaluationConfig


class TestEngineGameIntegration:
    """Verify custom engine interactions with Game service."""

    def test_engine_plays_valid_move_on_game(self) -> None:
        """The move chosen by the engine must be legally playable on the Game service."""
        game = Game("session-engine-test")
        # Human plays e4
        game.apply_move("e4")

        # Engine selects Black's move using Alpha-Beta
        config = SearchConfig(depth=2, algorithm="alpha_beta")
        result = choose_move(game.board, config)

        assert result.best_move is not None
        assert result.best_move_uci is not None

        # Apply engine move to Game service
        record = game.apply_move(result.best_move_uci)
        assert record.uci == result.best_move_uci
        assert game.turn == "white"
        assert len(game.get_state().san_history) == 2

    def test_engine_dispatches_minimax_and_alpha_beta(self) -> None:
        """Engine dispatches properly between minimax and alpha-beta algorithms."""
        board = chess.Board()

        minimax_cfg = SearchConfig(depth=2, algorithm="minimax")
        mm_res = choose_move(board, minimax_cfg)
        assert mm_res.algorithm == "minimax"

        ab_cfg = SearchConfig(depth=2, algorithm="alpha_beta")
        ab_res = choose_move(board, ab_cfg)
        assert ab_res.algorithm == "alpha_beta"

        # Scores must match
        assert ab_res.score_cp == mm_res.score_cp

    def test_invalid_search_config_rejected(self) -> None:
        with pytest.raises(ValueError):
            SearchConfig(depth=0)

        with pytest.raises(ValueError):
            SearchConfig(depth=2, algorithm="unsupported_algo")  # type: ignore

    def test_invalid_evaluation_config_rejected(self) -> None:
        with pytest.raises(ValueError):
            EvaluationConfig(pawn_value=-10)
