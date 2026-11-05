"""Benchmark script comparing all five difficulty profiles across 7 representative positions.

Measures:
- Selected move (UCI / SAN)
- Search evaluation score (centipawns, White-relative)
- Completed search depth
- Total nodes searched
- Quiescence search nodes
- Transposition Table stats (hits, cutoffs, stores)
- Allocated time budget (ms)
- Actual elapsed time (ms)
- Deadline compliance
"""

import math
import statistics
import time
from typing import Any, Dict, List
import chess

from engine import choose_move
from engine.difficulty import DIFFICULTY_PROFILES, DifficultyLevel

BENCHMARK_POSITIONS = [
    {
        "id": "P1",
        "name": "Starting Position",
        "fen": chess.STARTING_FEN,
    },
    {
        "id": "P2",
        "name": "Open Middlegame",
        "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5",
    },
    {
        "id": "P3",
        "name": "Closed Middlegame",
        "fen": "r2q1rk1/1b2bppp/p1n1pn2/1pp5/3PP3/2NB1N2/PP3PPP/R1BQR1K1 w - - 0 12",
    },
    {
        "id": "P4",
        "name": "Tactical Position",
        "fen": "r1bqk2r/pppp1ppp/2n5/4P3/1bB1n3/2N2N2/PPPP1PPP/R1BQK2R b KQkq - 2 6",
    },
    {
        "id": "P5",
        "name": "Check Position",
        "fen": "rnb1kbnr/ppppqppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1",
    },
    {
        "id": "P6",
        "name": "Rook Endgame",
        "fen": "8/5pk1/4p1p1/7p/3R3P/6P1/5PK1/4r3 w - - 0 40",
    },
    {
        "id": "P7",
        "name": "Symmetrical Position",
        "fen": "r1bq1rk1/ppp1bppp/2n1pn2/3p4/3P4/2N1PN2/PPP1BPPP/R1BQ1RK1 w - - 4 7",
    },
]

PROFILES = [
    DifficultyLevel.BEGINNER,
    DifficultyLevel.EASY,
    DifficultyLevel.MEDIUM,
    DifficultyLevel.HARD,
    DifficultyLevel.EXPERT,
]


def calculate_p95(values: List[float]) -> float:
    """Calculates the 95th percentile using linear interpolation between nearest ranks."""
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * 0.95
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    weight = k - f
    return round((1.0 - weight) * sorted_vals[f] + weight * sorted_vals[c], 1)


def run_benchmark(num_runs: int = 5) -> List[Dict[str, Any]]:
    """
    Runs search across all profiles and positions over repeated trials.
    
    Collects:
    - Number of runs
    - Median elapsed time (ms)
    - p95 elapsed time (ms)
    - Maximum elapsed time (ms)
    - Allocated deadline and effective search budget (ms)
    - Number of deadline misses
    - Completed depth, nodes, quiescence nodes, and TT cutoffs
    """
    results: List[Dict[str, Any]] = []

    header = (
        f"{'Pos':<4} | {'Name':<19} | {'Profile':<8} | {'Move':<6} | {'Depth':<5} | "
        f"{'Nodes':<7} | {'Q-Nodes':<7} | {'TTCut':<5} | {'Alloc':<7} | {'EffLim':<7} | "
        f"{'Runs':<4} | {'Median':<7} | {'p95':<7} | {'Max':<7} | {'Misses':<6}"
    )
    print(header)
    print("-" * len(header))

    for pos in BENCHMARK_POSITIONS:
        board = chess.Board(pos["fen"])
        for lvl in PROFILES:
            profile_name = lvl.value
            latencies: List[float] = []
            last_res = None

            for run_idx in range(num_runs):
                res = choose_move(board, difficulty=profile_name)
                latencies.append(res.elapsed_ms)
                last_res = res

            alloc_time = round(last_res.allocated_time_ms or 0.0, 1)
            prof = DIFFICULTY_PROFILES[lvl]
            eff_limit = round(max(prof.min_time_ms, alloc_time - 50.0), 1)

            median_elapsed = round(statistics.median(latencies), 1)
            p95_elapsed = calculate_p95(latencies)
            max_elapsed = round(max(latencies), 1)
            deadline_misses = sum(1 for lat in latencies if lat > alloc_time)

            record = {
                "pos_id": pos["id"],
                "pos_name": pos["name"],
                "profile": profile_name,
                "move_uci": last_res.best_move_uci or "none",
                "move_san": last_res.best_move_san or "none",
                "score_cp": last_res.score_cp,
                "completed_depth": last_res.completed_depth,
                "nodes": last_res.nodes_searched,
                "q_nodes": last_res.quiescence_nodes,
                "tt_hits": last_res.tt_hits,
                "tt_cutoffs": last_res.tt_cutoffs,
                "allocated_ms": alloc_time,
                "effective_limit_ms": eff_limit,
                "num_runs": num_runs,
                "median_ms": median_elapsed,
                "p95_ms": p95_elapsed,
                "max_ms": max_elapsed,
                "deadline_misses": deadline_misses,
            }
            results.append(record)

            print(
                f"{pos['id']:<4} | {pos['name'][:19]:<19} | {profile_name:<8} | "
                f"{record['move_uci']:<6} | {record['completed_depth']:<5} | "
                f"{record['nodes']:<7d} | {record['q_nodes']:<7d} | {record['tt_cutoffs']:<5d} | "
                f"{record['allocated_ms']:<7.1f} | {record['effective_limit_ms']:<7.1f} | "
                f"{record['num_runs']:<4d} | {record['median_ms']:<7.1f} | {record['p95_ms']:<7.1f} | "
                f"{record['max_ms']:<7.1f} | {record['deadline_misses']:<6d}"
            )

    return results


if __name__ == "__main__":
    run_benchmark(num_runs=5)
