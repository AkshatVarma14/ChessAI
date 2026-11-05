"""Population management and statistical tracking for the Genetic Algorithm."""

import math
import random
from typing import Dict, List, Optional

from engine.tuning.individual import GENE_SPECS, Individual
from engine.tuning.mutation import mutate_individual


class Population:
    """
    Manages a generation of candidate Individuals in the Genetic Algorithm.

    Tracks individual candidates, extracts elites, and computes population-level
    diversity and fitness statistics.
    """

    def __init__(
        self,
        individuals: List[Individual],
        generation: int = 0,
    ) -> None:
        """
        Initializes a Population with a list of Individuals.

        Args:
            individuals: List of candidate Individuals (must have at least 2).
            generation: Current generation index (0-indexed).
        """
        if len(individuals) < 2:
            raise ValueError(f"Population must have at least 2 individuals, got {len(individuals)}")
        self.individuals = individuals
        self.generation = generation

    def __len__(self) -> int:
        return len(self.individuals)

    def __getitem__(self, index: int) -> Individual:
        return self.individuals[index]

    def __iter__(self):
        return iter(self.individuals)

    @classmethod
    def create_initial(
        cls,
        population_size: int = 12,
        baseline: Optional[Individual] = None,
        perturbation_magnitude: float = 0.12,
        random_state: Optional[random.Random] = None,
    ) -> "Population":
        """
        Creates an initial generation containing the baseline individual and diverse variants.

        Guarantees that the exact handcrafted baseline is member 0 of the population.

        Args:
            population_size: Total number of individuals in the population (minimum 2).
            baseline: Optional reference Individual; defaults to engine baseline.
            perturbation_magnitude: Magnitude of mutations applied to seeded variants.
            random_state: Optional random generator for reproducible generation.

        Returns:
            Initialized generation 0 Population.
        """
        if population_size < 2:
            raise ValueError(f"population_size must be >= 2, got {population_size}")

        base = baseline.clone() if baseline is not None else Individual.create_baseline()
        members: List[Individual] = [base]

        rng = random_state or random

        # Create population_size - 1 mutated / explored variants
        for i in range(1, population_size):
            variant = base.clone()
            # Mutate with probability 0.5 for each gene
            mutate_individual(
                variant,
                mutation_rate=0.5,
                mutation_magnitude=perturbation_magnitude,
                random_state=rng,
            )
            members.append(variant)

        return cls(individuals=members, generation=0)

    def get_best(self) -> Individual:
        """Returns the individual with the highest fitness."""
        evaluated = [ind for ind in self.individuals if ind.fitness is not None]
        if not evaluated:
            raise ValueError("No individuals in population have evaluated fitness")
        return max(evaluated, key=lambda ind: ind.fitness)  # type: ignore

    def get_elites(self, count: int) -> List[Individual]:
        """
        Returns cloned copies of the top `count` fittest individuals.

        Args:
            count: Number of elite individuals to extract.

        Returns:
            List of cloned Individuals preserving their fitness scores.
        """
        if count < 1:
            return []
        evaluated = [ind for ind in self.individuals if ind.fitness is not None]
        sorted_elites = sorted(
            evaluated,
            key=lambda ind: ind.fitness,  # type: ignore
            reverse=True,
        )
        return [ind.clone() for ind in sorted_elites[:count]]

    def statistics(self) -> Dict[str, float]:
        """
        Computes fitness and diversity statistics for the current population.

        Returns:
            Dictionary containing best_fitness, mean_fitness, std_fitness, min_fitness, and diversity.
        """
        fits = [ind.fitness for ind in self.individuals if ind.fitness is not None]
        if not fits:
            return {
                "best_fitness": 0.0,
                "mean_fitness": 0.0,
                "std_fitness": 0.0,
                "min_fitness": 0.0,
                "diversity": 0.0,
            }

        best = max(fits)
        worst = min(fits)
        mean = sum(fits) / len(fits)
        variance = sum((f - mean) ** 2 for f in fits) / len(fits)
        std = math.sqrt(variance)

        # Compute gene diversity: average std across all normalized gene dimensions
        gene_stds: List[float] = []
        for spec in GENE_SPECS:
            span = float(spec.max_value - spec.min_value)
            norm_vals = [(float(ind.genes[spec.name]) - spec.min_value) / span for ind in self.individuals]
            g_mean = sum(norm_vals) / len(norm_vals)
            g_var = sum((v - g_mean) ** 2 for v in norm_vals) / len(norm_vals)
            gene_stds.append(math.sqrt(g_var))

        diversity = sum(gene_stds) / len(gene_stds) if gene_stds else 0.0

        return {
            "best_fitness": round(best, 4),
            "mean_fitness": round(mean, 4),
            "std_fitness": round(std, 4),
            "min_fitness": round(worst, 4),
            "diversity": round(diversity, 4),
        }
