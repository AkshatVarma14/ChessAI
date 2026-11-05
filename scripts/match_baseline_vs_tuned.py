"""Controlled match runner comparing Baseline handcrafted weights vs Tuned weights.

Plays paired color-swapped games across canonical opening positions using identical
search budgets to empirically explore gameplay divergence and tactical behavior.
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import chess
from engine import EvaluationConfig, SearchConfig, choose_move
from engine.evaluation.evaluator import evaluate_position
from engine.tuning import GAResult


@dataclass
class GameRecord:
    """Summary record of an individual match game."""

    game_id: int
    opening_name: str
    white_name: str
    black_name: str
    result_str: str
    winner_name: Optional[str]
    termination_reason: str
    plies_played: int
    elapsed_seconds: float
    final_fen: str


OPENING_SUITE: List[Tuple[str, str]] = [
    ("Standard Starting Position", chess.STARTING_FEN),
    ("Open Game (Italian/Spanish entry)", "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"),
    ("Sicilian Defense Tension", "rnbqkbnr/pp2pppp/3p4/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3"),
    ("Queen's Gambit Declined", "rnbqkbnr/ppp2ppp/4p3/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3"),
]


def play_game(
    game_id: int,
    opening_name: str,
    start_fen: str,
    white_name: str,
    black_name: str,
    white_cfg: EvaluationConfig,
    black_cfg: EvaluationConfig,
    search_cfg: SearchConfig,
    max_plies: int = 50,
) -> GameRecord:
    """Simulates a complete game between two evaluation configurations."""
    board = chess.Board(start_fen)
    t0 = time.perf_counter()
    plies = 0

    while not board.is_game_over() and plies < max_plies:
        active_cfg = white_cfg if board.turn == chess.WHITE else black_cfg
        res = choose_move(board, config=search_cfg, eval_config=active_cfg)
        if not res.best_move or not board.is_legal(res.best_move):
            break
        board.push(res.best_move)
        plies += 1

    elapsed = time.perf_counter() - t0

    # Determine outcome
    outcome = board.outcome()
    if outcome is not None:
        if outcome.winner == chess.WHITE:
            result_str = "1-0"
            winner_name = white_name
            reason = f"Checkmate by {white_name}" if board.is_checkmate() else outcome.termination.name
        elif outcome.winner == chess.BLACK:
            result_str = "0-1"
            winner_name = black_name
            reason = f"Checkmate by {black_name}" if board.is_checkmate() else outcome.termination.name
        else:
            result_str = "1/2-1/2"
            winner_name = None
            reason = outcome.termination.name
    else:
        # Reached move limit: evaluate material/positional balance
        final_score = evaluate_position(board)
        if final_score > 150:
            result_str = "1-0"
            winner_name = white_name
            reason = f"Move limit reached ({final_score} cp for White)"
        elif final_score < -150:
            result_str = "0-1"
            winner_name = black_name
            reason = f"Move limit reached ({-final_score} cp for Black)"
        else:
            result_str = "1/2-1/2"
            winner_name = None
            reason = f"Move limit draw (balanced {final_score} cp)"

    return GameRecord(
        game_id=game_id,
        opening_name=opening_name,
        white_name=white_name,
        black_name=black_name,
        result_str=result_str,
        winner_name=winner_name,
        termination_reason=reason,
        plies_played=plies,
        elapsed_seconds=round(elapsed, 2),
        final_fen=board.fen(),
    )


def main() -> int:
    config_path = "experiments/tuned_weights.json"
    if not Path(config_path).is_file():
        print(f"Error: {config_path} not found. Run scripts/run_ga_tuning.py first.")
        return 1

    tuned_cfg = GAResult.load_tuned_config(config_path)
    base_cfg = EvaluationConfig()

    search_cfg = SearchConfig(
        depth=2,
        use_move_ordering=True,
        use_quiescence=True,
        max_quiescence_depth=2,
        max_nodes=3000,
    )

    print("=" * 85)
    print("  CONTROLLED SELF-PLAY MATCH: HANDCRAFTED BASELINE VS TUNED CANDIDATE")
    print("=" * 85)
    print(f"Opening Positions     : {len(OPENING_SUITE)} canonical positions")
    print(f"Color Swapping        : 2 games per opening (8 total paired games)")
    print(f"Search Configuration  : Depth {search_cfg.depth}, Quiescence Depth {search_cfg.max_quiescence_depth}, Ordering=True")
    print(f"Move Ceiling per Game : 50 plies")
    print("=" * 85)

    records: List[GameRecord] = []
    game_idx = 1

    for opening_name, fen in OPENING_SUITE:
        # Game A: Tuned (White) vs Baseline (Black)
        rec_a = play_game(
            game_id=game_idx,
            opening_name=opening_name,
            start_fen=fen,
            white_name="Tuned",
            black_name="Baseline",
            white_cfg=tuned_cfg,
            black_cfg=base_cfg,
            search_cfg=search_cfg,
        )
        records.append(rec_a)
        print(f"Game {rec_a.game_id:<2}: [White: {rec_a.white_name:<8} vs Black: {rec_a.black_name:<8}] -> {rec_a.result_str:<7} ({rec_a.termination_reason}, {rec_a.plies_played} plies, {rec_a.elapsed_seconds}s)")
        game_idx += 1

        # Game B: Baseline (White) vs Tuned (Black)
        rec_b = play_game(
            game_id=game_idx,
            opening_name=opening_name,
            start_fen=fen,
            white_name="Baseline",
            black_name="Tuned",
            white_cfg=base_cfg,
            black_cfg=tuned_cfg,
            search_cfg=search_cfg,
        )
        records.append(rec_b)
        print(f"Game {rec_b.game_id:<2}: [White: {rec_b.white_name:<8} vs Black: {rec_b.black_name:<8}] -> {rec_b.result_str:<7} ({rec_b.termination_reason}, {rec_b.plies_played} plies, {rec_b.elapsed_seconds}s)")
        game_idx += 1

    print("=" * 85)
    print("  MATCH RESULTS SUMMARY")
    print("=" * 85)

    tuned_wins = sum(1 for r in records if r.winner_name == "Tuned")
    base_wins = sum(1 for r in records if r.winner_name == "Baseline")
    draws = sum(1 for r in records if r.winner_name is None)
    tuned_points = tuned_wins + 0.5 * draws
    base_points = base_wins + 0.5 * draws
    total_games = len(records)

    print(f"Total Games Played    : {total_games}")
    print(f"Tuned Configuration   : {tuned_wins} Wins, {base_wins} Losses, {draws} Draws ({tuned_points}/{total_games} points, {tuned_points/total_games*100:.1f}%)")
    print(f"Baseline Configuration: {base_wins} Wins, {tuned_wins} Losses, {draws} Draws ({base_points}/{total_games} points, {base_points/total_games*100:.1f}%)")
    print("=" * 85)
    print("NOTE: Self-play matches between slightly modified evaluation parameters provide")
    print("exploratory insight into tactical divergence and behavioral stability, but cannot")
    print("serve as an independent ground truth of playing strength (Elo).")
    print("=" * 85)

    return 0


if __name__ == "__main__":
    sys.exit(main())
