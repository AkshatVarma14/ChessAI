"""Command-line script for running the Genetic Algorithm evaluation weight optimizer.

Allows executing reproducible offline tuning experiments, monitoring generation
progress, comparing tuned candidates against the baseline on held-out validation
positions, and exporting tuned weights to JSON.
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.tuning import (
    GENE_SPECS,
    GAConfig,
    GAResult,
    GenerationTelemetry,
    GeneticAlgorithm,
    get_training_suite,
    get_validation_suite,
)


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Formats a clean plaintext markdown-like table."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    row_lines = [
        " | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(row))
        for row in rows
    ]
    return f"{header_line}\n{sep_line}\n" + "\n".join(row_lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline Genetic Algorithm Tuning for Handcrafted Chess Evaluation Weights"
    )
    parser.add_argument(
        "-g", "--generations", type=int, default=5, help="Number of generations to evolve (default: 5)"
    )
    parser.add_argument(
        "-p", "--pop-size", type=int, default=12, help="Population size per generation (default: 12)"
    )
    parser.add_argument(
        "-e", "--elites", type=int, default=2, help="Number of elite individuals to preserve (default: 2)"
    )
    parser.add_argument(
        "-s", "--seed", type=int, default=42, help="Random seed for deterministic reproducibility (default: 42)"
    )
    parser.add_argument(
        "--crossover-rate", type=float, default=0.80, help="Crossover probability (default: 0.80)"
    )
    parser.add_argument(
        "--mutation-rate", type=float, default=0.25, help="Mutation probability per gene (default: 0.25)"
    )
    parser.add_argument(
        "--mutation-mag", type=float, default=0.15, help="Mutation magnitude as fraction of gene span (default: 0.15)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Evaluate Generation 0 and exit immediately"
    )
    parser.add_argument(
        "--export",
        type=str,
        default="experiments/tuned_weights.json",
        help="Destination JSON filepath for tuned weights (default: experiments/tuned_weights.json)",
    )

    args = parser.parse_args()

    train_suite = get_training_suite()
    val_suite = get_validation_suite()

    print("=" * 80)
    print("  CHESS AI EVALUATION WEIGHT TUNING — GENETIC ALGORITHM")
    print("=" * 80)
    print(f"Target Parameters     : 12 Handcrafted Evaluation Weights")
    print(f"Training Positions    : {len(train_suite)} positions")
    print(f"Validation Positions  : {len(val_suite)} held-out positions (NEVER seen during evolution)")
    print(f"Generations           : {args.generations}")
    print(f"Population Size       : {args.pop_size}")
    print(f"Elites Preserved      : {args.elites}")
    print(f"Random Seed           : {args.seed}")
    print(f"Dry Run Mode          : {'ENABLED' if args.dry_run else 'DISABLED'}")
    print(f"Export Target         : {args.export}")
    print("=" * 80)

    print("\nStarting optimization run...\n")
    print(f"{'Gen':<5} | {'Best Fit':<10} | {'Mean Fit':<10} | {'Std Fit':<10} | {'Diversity':<10} | {'Time (s)':<10}")
    print("-" * 65)

    def progress_callback(t: GenerationTelemetry) -> None:
        print(
            f"{t.generation:<5} | {t.best_fitness:<10.4f} | {t.mean_fitness:<10.4f} | "
            f"{t.std_fitness:<10.4f} | {t.diversity:<10.4f} | {t.elapsed_seconds:<10.3f}"
        )

    config = GAConfig(
        generations=args.generations,
        population_size=args.pop_size,
        elite_count=args.elites,
        crossover_rate=args.crossover_rate,
        mutation_rate=args.mutation_rate,
        mutation_magnitude=args.mutation_mag,
        random_seed=args.seed,
        dry_run=args.dry_run,
        progress_callback=progress_callback,
    )

    optimizer = GeneticAlgorithm(config=config)
    result = optimizer.run()

    print("-" * 65)
    print(f"Optimization completed in {result.total_duration_seconds:.2f} seconds.\n")

    # Export configuration
    result.export_tuned_config(args.export)
    print(f"Tuned weights exported successfully to: {args.export}\n")

    # Print baseline vs tuned comparison table
    print("=" * 80)
    print("  TUNED PARAMETERS VS HANDCRAFTED BASELINE")
    print("=" * 80)
    table_headers = ["Gene Name", "Type", "Baseline", "Tuned", "Bounds [Min, Max]"]
    table_rows = []
    for spec in GENE_SPECS:
        base_val = spec.baseline
        tuned_val = result.best_individual.genes[spec.name]
        bounds_str = f"[{spec.min_value}, {spec.max_value}]"
        table_rows.append([spec.name, spec.gene_type.__name__, str(base_val), str(tuned_val), bounds_str])

    print(format_table(table_headers, table_rows))

    print("\n" + "=" * 80)
    print("  PERFORMANCE METRICS SUMMARY")
    print("=" * 80)
    metrics_headers = ["Metric", "Baseline", "Tuned Best", "Delta"]
    delta_train = result.best_fitness - result.baseline_fitness
    val_base_fit = result.baseline_validation.get("validation_fitness", 0.0)
    val_best_fit = result.best_validation.get("validation_fitness", 0.0)
    delta_val = val_best_fit - val_base_fit

    base_val_pos_acc = result.baseline_validation.get("positional_accuracy", 0.0)
    best_val_pos_acc = result.best_validation.get("positional_accuracy", 0.0)
    base_val_tac_acc = result.baseline_validation.get("tactical_accuracy", 0.0)
    best_val_tac_acc = result.best_validation.get("tactical_accuracy", 0.0)

    metrics_rows = [
        ["Training Fitness (Composite)", f"{result.baseline_fitness:.4f}", f"{result.best_fitness:.4f}", f"{delta_train:+.4f}"],
        ["Validation Fitness (Held-out)", f"{val_base_fit:.4f}", f"{val_best_fit:.4f}", f"{delta_val:+.4f}"],
        ["Validation Positional Acc (%)", f"{base_val_pos_acc:.2f}%", f"{best_val_pos_acc:.2f}%", f"{best_val_pos_acc - base_val_pos_acc:+.2f}%"],
        ["Validation Tactical Acc (%)", f"{base_val_tac_acc:.2f}%", f"{best_val_tac_acc:.2f}%", f"{best_val_tac_acc - base_val_tac_acc:+.2f}%"],
    ]
    print(format_table(metrics_headers, metrics_rows))
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
