"""Offline Genetic Algorithm tuning package for chess engine evaluation weights."""

from engine.tuning.crossover import blend_crossover, uniform_crossover
from engine.tuning.dataset import (
    INDEPENDENT_SUITE,
    TuningPosition,
    get_independent_suite,
    get_training_suite,
    get_validation_suite,
)
from engine.tuning.fitness import FitnessConfig, FitnessEvaluator
from engine.tuning.genetic_algorithm import GAConfig, GeneticAlgorithm
from engine.tuning.individual import GENE_MAP, GENE_SPECS, GeneSpec, Individual
from engine.tuning.mutation import mutate_individual
from engine.tuning.population import Population
from engine.tuning.results import GAResult, GenerationTelemetry
from engine.tuning.selection import rank_selection, tournament_selection

__all__ = [
    "GeneSpec",
    "GENE_SPECS",
    "GENE_MAP",
    "Individual",
    "TuningPosition",
    "get_training_suite",
    "get_validation_suite",
    "get_independent_suite",
    "INDEPENDENT_SUITE",
    "FitnessConfig",
    "FitnessEvaluator",
    "tournament_selection",
    "rank_selection",
    "blend_crossover",
    "uniform_crossover",
    "mutate_individual",
    "Population",
    "GAConfig",
    "GeneticAlgorithm",
    "GAResult",
    "GenerationTelemetry",
]
