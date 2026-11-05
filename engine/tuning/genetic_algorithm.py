"""Core Genetic Algorithm optimizer for chess evaluation weights.

Executes offline tuning with elitism, tournament selection, BLX-alpha crossover,
Gaussian perturbation mutation, reproducible seeds, and dry-run execution.
"""

from copy import deepcopy
from dataclasses import dataclass
import random
import time
from typing import Callable, List, Optional

from engine.tuning.crossover import blend_crossover
from engine.tuning.fitness import FitnessConfig, FitnessEvaluator
from engine.tuning.individual import Individual
from engine.tuning.mutation import mutate_individual
from engine.tuning.population import Population
from engine.tuning.results import GAResult, GenerationTelemetry
from engine.tuning.selection import tournament_selection


@dataclass
class GAConfig:
    """
    Configuration options for the Genetic Algorithm tuning process.

    Attributes:
        generations: Maximum number of generations to run.
        population_size: Total number of individuals in each generation.
        elite_count: Number of fittest individuals carried forward directly.
        tournament_size: Size of tournament for selection.
        crossover_rate: Probability of performing crossover on selected parents.
        crossover_alpha: BLX-alpha exploration width.
        mutation_rate: Probability of mutating each gene in an offspring.
        mutation_magnitude: Mutation standard deviation relative to gene span.
        random_seed: Optional integer seed for exact deterministic reproducibility.
        dry_run: When True, initializes generation 0, evaluates baseline, and stops immediately.
        early_stopping_generations: Optional patience threshold before early termination.
        progress_callback: Optional callable receiving GenerationTelemetry after each generation.
    """

    generations: int = 5
    population_size: int = 12
    elite_count: int = 2
    tournament_size: int = 3
    crossover_rate: float = 0.80
    crossover_alpha: float = 0.30
    mutation_rate: float = 0.25
    mutation_magnitude: float = 0.15
    random_seed: Optional[int] = None
    dry_run: bool = False
    early_stopping_generations: Optional[int] = None
    progress_callback: Optional[Callable[[GenerationTelemetry], None]] = None

    def __post_init__(self) -> None:
        if self.generations < 1:
            raise ValueError(f"generations must be >= 1, got {self.generations}")
        if self.population_size < 2:
            raise ValueError(f"population_size must be >= 2, got {self.population_size}")
        if self.elite_count < 0 or self.elite_count >= self.population_size:
            raise ValueError(
                f"elite_count must be between 0 and population_size - 1, got {self.elite_count}"
            )
        if not (0.0 <= self.crossover_rate <= 1.0):
            raise ValueError(f"crossover_rate must be between 0 and 1, got {self.crossover_rate}")
        if not (0.0 <= self.mutation_rate <= 1.0):
            raise ValueError(f"mutation_rate must be between 0 and 1, got {self.mutation_rate}")


class GeneticAlgorithm:
    """
    Orchestrates offline evaluation weight tuning using genetic search.

    Completely decoupled from runtime web services and external engine dependencies.
    """

    def __init__(
        self,
        config: Optional[GAConfig] = None,
        fitness_evaluator: Optional[FitnessEvaluator] = None,
    ) -> None:
        """
        Initializes the Genetic Algorithm optimizer.

        Args:
            config: Optimization parameters; defaults to GAConfig().
            fitness_evaluator: Fitness evaluation harness; defaults to FitnessEvaluator().
        """
        self.config = config or GAConfig()
        self.evaluator = fitness_evaluator or FitnessEvaluator()
        self._rng = random.Random(self.config.random_seed)

    def run(self) -> GAResult:
        """
        Executes the Genetic Algorithm optimization loop.

        Returns:
            Complete GAResult detailing evolution history and validation comparisons.
        """
        start_time = time.perf_counter()

        # 1. Evaluate Handcrafted Baseline
        baseline = Individual.create_baseline()
        self.evaluator.evaluate(baseline)
        baseline_fitness = baseline.fitness if baseline.fitness is not None else 0.0
        baseline_breakdown = dict(baseline.fitness_breakdown or {})
        baseline_validation = self.evaluator.evaluate_validation(baseline)

        # 2. Initialize Population (Generation 0)
        population = Population.create_initial(
            population_size=self.config.population_size,
            baseline=baseline,
            perturbation_magnitude=self.config.mutation_magnitude,
            random_state=self._rng,
        )

        history: List[GenerationTelemetry] = []
        best_overall = baseline.clone()
        no_improvement_streak = 0

        # Evaluate Generation 0
        self._evaluate_population(population)
        gen_stats = population.statistics()
        gen_best = population.get_best()

        if gen_best.fitness is not None and gen_best.fitness > (best_overall.fitness or 0.0):
            best_overall = gen_best.clone()

        elapsed = time.perf_counter() - start_time
        telemetry_gen0 = GenerationTelemetry(
            generation=0,
            best_fitness=gen_stats["best_fitness"],
            mean_fitness=gen_stats["mean_fitness"],
            std_fitness=gen_stats["std_fitness"],
            min_fitness=gen_stats["min_fitness"],
            diversity=gen_stats["diversity"],
            elapsed_seconds=round(elapsed, 3),
            best_genes=deepcopy(gen_best.genes),
            best_breakdown=deepcopy(gen_best.fitness_breakdown),
        )
        history.append(telemetry_gen0)

        if self.config.progress_callback:
            self.config.progress_callback(telemetry_gen0)

        # If dry run requested, terminate immediately after generation 0
        if self.config.dry_run:
            total_duration = time.perf_counter() - start_time
            best_val = self.evaluator.evaluate_validation(best_overall)
            return GAResult(
                total_generations=1,
                population_size=self.config.population_size,
                random_seed=self.config.random_seed,
                total_duration_seconds=total_duration,
                baseline_fitness=baseline_fitness,
                baseline_breakdown=baseline_breakdown,
                baseline_validation=baseline_validation,
                best_fitness=best_overall.fitness or 0.0,
                best_individual=best_overall,
                best_validation=best_val,
                history=history,
            )

        # 3. Evolution Loop
        for gen in range(1, self.config.generations):
            # Extract elites
            elites = population.get_elites(self.config.elite_count)
            next_individuals: List[Individual] = list(elites)

            # Generate offspring to fill population
            while len(next_individuals) < self.config.population_size:
                parent1 = tournament_selection(
                    population.individuals,
                    tournament_size=self.config.tournament_size,
                    random_state=self._rng,
                )
                parent2 = tournament_selection(
                    population.individuals,
                    tournament_size=self.config.tournament_size,
                    random_state=self._rng,
                )

                # Crossover
                if self._rng.random() < self.config.crossover_rate:
                    child1, child2 = blend_crossover(
                        parent1,
                        parent2,
                        alpha=self.config.crossover_alpha,
                        random_state=self._rng,
                    )
                else:
                    child1, child2 = parent1.clone(), parent2.clone()
                    child1.fitness = None
                    child2.fitness = None

                # Mutation
                mutate_individual(
                    child1,
                    mutation_rate=self.config.mutation_rate,
                    mutation_magnitude=self.config.mutation_magnitude,
                    random_state=self._rng,
                )
                next_individuals.append(child1)

                if len(next_individuals) < self.config.population_size:
                    mutate_individual(
                        child2,
                        mutation_rate=self.config.mutation_rate,
                        mutation_magnitude=self.config.mutation_magnitude,
                        random_state=self._rng,
                    )
                    next_individuals.append(child2)

            population = Population(individuals=next_individuals, generation=gen)
            self._evaluate_population(population)

            gen_stats = population.statistics()
            gen_best = population.get_best()

            # Track overall best
            current_best_fit = best_overall.fitness or 0.0
            if gen_best.fitness is not None and gen_best.fitness > current_best_fit:
                best_overall = gen_best.clone()
                no_improvement_streak = 0
            else:
                no_improvement_streak += 1

            elapsed = time.perf_counter() - start_time
            telemetry = GenerationTelemetry(
                generation=gen,
                best_fitness=gen_stats["best_fitness"],
                mean_fitness=gen_stats["mean_fitness"],
                std_fitness=gen_stats["std_fitness"],
                min_fitness=gen_stats["min_fitness"],
                diversity=gen_stats["diversity"],
                elapsed_seconds=round(elapsed, 3),
                best_genes=deepcopy(gen_best.genes),
                best_breakdown=deepcopy(gen_best.fitness_breakdown),
            )
            history.append(telemetry)

            if self.config.progress_callback:
                self.config.progress_callback(telemetry)

            # Check early stopping condition
            if (
                self.config.early_stopping_generations is not None
                and no_improvement_streak >= self.config.early_stopping_generations
            ):
                break

        total_duration = time.perf_counter() - start_time

        # 4. Final Validation Evaluation
        best_validation = self.evaluator.evaluate_validation(best_overall)

        return GAResult(
            total_generations=len(history),
            population_size=self.config.population_size,
            random_seed=self.config.random_seed,
            total_duration_seconds=total_duration,
            baseline_fitness=baseline_fitness,
            baseline_breakdown=baseline_breakdown,
            baseline_validation=baseline_validation,
            best_fitness=best_overall.fitness or 0.0,
            best_individual=best_overall,
            best_validation=best_validation,
            history=history,
        )

    def _evaluate_population(self, population: Population) -> None:
        """Evaluates all individuals in the population that lack a fitness score."""
        for individual in population.individuals:
            if individual.fitness is None:
                self.evaluator.evaluate(individual)
