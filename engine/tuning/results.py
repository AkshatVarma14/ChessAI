"""Results data structures and serialization for the Genetic Algorithm."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.config import EvaluationConfig
from engine.tuning.individual import Individual


@dataclass
class GenerationTelemetry:
    """Telemetry recorded for a single generation of the GA run."""

    generation: int
    best_fitness: float
    mean_fitness: float
    std_fitness: float
    min_fitness: float
    diversity: float
    elapsed_seconds: float
    best_genes: Dict[str, Any]
    best_breakdown: Optional[Dict[str, float]] = None


@dataclass
class GAResult:
    """
    Comprehensive record of a complete Genetic Algorithm tuning run.

    Encapsulates evolution history, baseline vs. best comparisons, held-out
    validation metrics, and serialization helpers.
    """

    total_generations: int
    population_size: int
    random_seed: Optional[int]
    total_duration_seconds: float
    baseline_fitness: float
    baseline_breakdown: Dict[str, float]
    baseline_validation: Dict[str, Any]
    best_fitness: float
    best_individual: Individual
    best_validation: Dict[str, Any]
    history: List[GenerationTelemetry]

    def export_tuned_config(self, filepath: str) -> None:
        """
        Exports the best tuned individual's parameters as a versioned JSON configuration.

        Args:
            filepath: Destination file path (e.g. 'experiments/tuned_weights.json').
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "format_version": "1.0",
                "total_generations": self.total_generations,
                "population_size": self.population_size,
                "random_seed": self.random_seed,
                "duration_seconds": round(self.total_duration_seconds, 2),
                "baseline_training_fitness": self.baseline_fitness,
                "best_training_fitness": self.best_fitness,
                "baseline_validation_fitness": self.baseline_validation.get("validation_fitness"),
                "best_validation_fitness": self.best_validation.get("validation_fitness"),
            },
            "genes": self.best_individual.genes,
            "training_breakdown": self.best_individual.fitness_breakdown,
            "validation_breakdown": self.best_validation,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_tuned_config(cls, filepath: str) -> EvaluationConfig:
        """
        Loads a tuned JSON configuration file directly into an EvaluationConfig.

        Args:
            filepath: Path to the JSON file exported by export_tuned_config.

        Returns:
            Ready-to-use EvaluationConfig instance.
        """
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"Tuned config file not found: {filepath}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        genes = data.get("genes", {})
        individual = Individual(genes=genes)
        return individual.to_evaluation_config()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the complete GAResult to a dictionary."""
        return {
            "total_generations": self.total_generations,
            "population_size": self.population_size,
            "random_seed": self.random_seed,
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "baseline_fitness": self.baseline_fitness,
            "baseline_breakdown": self.baseline_breakdown,
            "baseline_validation": self.baseline_validation,
            "best_fitness": self.best_fitness,
            "best_individual": self.best_individual.to_dict(),
            "best_validation": self.best_validation,
            "history": [asdict(t) for t in self.history],
        }
