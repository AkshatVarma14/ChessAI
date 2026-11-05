"""Mutation operators for the Genetic Algorithm.

Implements bounded Gaussian perturbation mutation ensuring all genes
remain strictly within authorized physical ranges.
"""

import random
from typing import Optional

from engine.tuning.individual import GENE_SPECS, Individual


def mutate_individual(
    individual: Individual,
    mutation_rate: float = 0.25,
    mutation_magnitude: float = 0.15,
    random_state: Optional[random.Random] = None,
) -> Individual:
    """
    Applies Gaussian perturbation mutation to an individual's genes.

    For each gene with probability mutation_rate, adds zero-mean Gaussian noise
    proportional to the gene's authorized span, then clamps within boundaries.
    Resets fitness to None since gene values are modified.

    Args:
        individual: The Individual to mutate (modified in-place or returned).
        mutation_rate: Probability of mutating each individual gene (0.0 to 1.0).
        mutation_magnitude: Relative standard deviation as a fraction of gene span.
        random_state: Optional random generator for deterministic testing.

    Returns:
        The mutated Individual with cleared fitness.
    """
    rng = random_state or random

    for spec in GENE_SPECS:
        if rng.random() < mutation_rate:
            current_val = float(individual.genes[spec.name])
            span = float(spec.max_value - spec.min_value)
            sigma = mutation_magnitude * span
            delta = rng.gauss(0.0, sigma)
            new_val = current_val + delta

            # Clamp and typecast
            clamped = max(spec.min_value, min(spec.max_value, new_val))
            if spec.gene_type is int:
                individual.genes[spec.name] = int(round(clamped))
            else:
                individual.genes[spec.name] = round(clamped, 4)

    # Invalidate cached fitness scores
    individual.fitness = None
    individual.fitness_breakdown = None
    return individual
