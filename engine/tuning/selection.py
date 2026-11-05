"""Selection operators for the Genetic Algorithm.

Provides tournament, rank, and fitness-proportionate selection methods
with support for explicit random seeds to ensure full reproducibility.
"""

import random
from typing import List, Optional

from engine.tuning.individual import Individual


def tournament_selection(
    population: List[Individual],
    tournament_size: int = 3,
    random_state: Optional[random.Random] = None,
) -> Individual:
    """
    Selects the fittest individual from a randomly chosen tournament subset.

    Args:
        population: Pool of candidate individuals (must have evaluated fitness).
        tournament_size: Number of competitors in each tournament.
        random_state: Optional random.Random generator for reproducibility.

    Returns:
        The winning Individual with the highest fitness.

    Raises:
        ValueError: If population is empty or tournament_size is invalid.
    """
    if not population:
        raise ValueError("Population cannot be empty for tournament selection")
    if tournament_size < 1:
        raise ValueError(f"tournament_size must be >= 1, got {tournament_size}")

    rng = random_state or random
    k = min(tournament_size, len(population))
    contestants = rng.sample(population, k)

    # Sort contestants by fitness descending (None treated as -infinity)
    winner = max(contestants, key=lambda ind: ind.fitness if ind.fitness is not None else float("-inf"))
    return winner


def rank_selection(
    population: List[Individual],
    random_state: Optional[random.Random] = None,
) -> Individual:
    """
    Selects an individual using linear rank selection.

    Mitigates premature convergence by ranking candidates by fitness rather
    than using raw fitness ratios.

    Args:
        population: Pool of candidate individuals.
        random_state: Optional random.Random generator for reproducibility.

    Returns:
        Selected Individual.
    """
    if not population:
        raise ValueError("Population cannot be empty for rank selection")

    rng = random_state or random
    n = len(population)
    if n == 1:
        return population[0]

    # Sort ascending by fitness so rank 1 is worst, rank n is best
    sorted_pop = sorted(
        population,
        key=lambda ind: ind.fitness if ind.fitness is not None else float("-inf"),
    )

    # Total sum of ranks: 1 + 2 + ... + n = n * (n + 1) / 2
    total_ranks = n * (n + 1) / 2.0
    pick = rng.uniform(0.0, total_ranks)

    current = 0.0
    for rank, individual in enumerate(sorted_pop, start=1):
        current += rank
        if current >= pick:
            return individual

    return sorted_pop[-1]
