"""Crossover operators for the Genetic Algorithm.

Implements Blend Crossover (BLX-alpha) for bounded real/integer parameters
and Uniform Crossover for combinatorial gene exchange.
"""

import random
from typing import Optional, Tuple

from engine.tuning.individual import GENE_MAP, GENE_SPECS, Individual


def blend_crossover(
    parent1: Individual,
    parent2: Individual,
    alpha: float = 0.3,
    random_state: Optional[random.Random] = None,
) -> Tuple[Individual, Individual]:
    """
    Performs BLX-alpha (Blend Crossover) between two parent individuals.

    For each gene, samples uniformly within [min(p1, p2) - alpha*d, max(p1, p2) + alpha*d]
    where d = |p1 - p2|, then strictly clamps within the GeneSpec boundaries.

    Args:
        parent1: First parent individual.
        parent2: Second parent individual.
        alpha: Blend exploration coefficient (typically 0.1 to 0.5).
        random_state: Optional random generator for deterministic testing.

    Returns:
        Tuple containing two newly created offspring Individuals with unassigned fitness.
    """
    rng = random_state or random
    child1_genes = {}
    child2_genes = {}

    for spec in GENE_SPECS:
        name = spec.name
        v1 = float(parent1.genes[name])
        v2 = float(parent2.genes[name])

        low = min(v1, v2)
        high = max(v1, v2)
        diff = high - low

        range_min = low - alpha * diff
        range_max = high + alpha * diff

        # Generate two child gene values
        c1_val = rng.uniform(range_min, range_max)
        c2_val = rng.uniform(range_min, range_max)

        # Enforce gene type and boundary constraints
        if spec.gene_type is int:
            child1_genes[name] = int(round(max(spec.min_value, min(spec.max_value, c1_val))))
            child2_genes[name] = int(round(max(spec.min_value, min(spec.max_value, c2_val))))
        else:
            child1_genes[name] = round(max(spec.min_value, min(spec.max_value, c1_val)), 4)
            child2_genes[name] = round(max(spec.min_value, min(spec.max_value, c2_val)), 4)

    return Individual(genes=child1_genes), Individual(genes=child2_genes)


def uniform_crossover(
    parent1: Individual,
    parent2: Individual,
    swap_prob: float = 0.5,
    random_state: Optional[random.Random] = None,
) -> Tuple[Individual, Individual]:
    """
    Performs Uniform Crossover between two parent individuals.

    Each gene is inherited independently from parent1 or parent2 with probability swap_prob.

    Args:
        parent1: First parent individual.
        parent2: Second parent individual.
        swap_prob: Probability of swapping each gene between parents.
        random_state: Optional random generator.

    Returns:
        Tuple containing two offspring Individuals.
    """
    rng = random_state or random
    child1_genes = {}
    child2_genes = {}

    for spec in GENE_SPECS:
        name = spec.name
        if rng.random() < swap_prob:
            child1_genes[name] = parent2.genes[name]
            child2_genes[name] = parent1.genes[name]
        else:
            child1_genes[name] = parent1.genes[name]
            child2_genes[name] = parent2.genes[name]

    return Individual(genes=child1_genes), Individual(genes=child2_genes)
