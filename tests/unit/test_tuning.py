"""Unit tests for the Genetic Algorithm evaluation weight tuning system."""

import json
from pathlib import Path
import random

import chess
import pytest

from engine.config import EvaluationConfig
from engine.constants import (
    DEFAULT_BISHOP_VALUE,
    DEFAULT_KNIGHT_VALUE,
    DEFAULT_PAWN_VALUE,
    DEFAULT_QUEEN_VALUE,
    DEFAULT_ROOK_VALUE,
)
from engine.evaluation.evaluator import evaluate_position
from engine.tuning import (
    GENE_MAP,
    GENE_SPECS,
    FitnessConfig,
    FitnessEvaluator,
    GAConfig,
    GAResult,
    GenerationTelemetry,
    GeneticAlgorithm,
    Individual,
    Population,
    blend_crossover,
    get_training_suite,
    get_validation_suite,
    mutate_individual,
    rank_selection,
    tournament_selection,
    uniform_crossover,
)


class TestGeneSpecsAndIndividual:
    """Tests for GeneSpec, parameter boundaries, and Individual representations."""

    def test_exactly_twelve_tunable_genes(self) -> None:
        """Verifies exactly 12 tunable genes are registered in GeneSpecs."""
        assert len(GENE_SPECS) == 12
        assert len(GENE_MAP) == 12

    def test_gene_specs_boundary_invariants(self) -> None:
        """Verifies all gene specifications have strictly positive ranges and valid baselines."""
        for spec in GENE_SPECS:
            assert spec.min_value < spec.max_value
            assert spec.min_value <= spec.baseline <= spec.max_value
            if spec.gene_type is int:
                assert isinstance(spec.baseline, int)
                assert isinstance(spec.min_value, int)
                assert isinstance(spec.max_value, int)
            else:
                assert isinstance(spec.baseline, float)

    def test_create_baseline_matches_engine_constants(self) -> None:
        """Verifies baseline individual genes match authoritative engine constants."""
        ind = Individual.create_baseline()
        assert ind.genes["pawn_value"] == DEFAULT_PAWN_VALUE
        assert ind.genes["knight_value"] == DEFAULT_KNIGHT_VALUE
        assert ind.genes["bishop_value"] == DEFAULT_BISHOP_VALUE
        assert ind.genes["rook_value"] == DEFAULT_ROOK_VALUE
        assert ind.genes["queen_value"] == DEFAULT_QUEEN_VALUE
        assert ind.genes["material_weight"] == 1.0
        assert ind.genes["pst_weight"] == 1.0
        assert ind.genes["mobility_weight"] == 1.0
        assert ind.genes["pawn_structure_weight"] == 1.0
        assert ind.genes["center_control_weight"] == 1.0
        assert ind.genes["king_safety_weight"] == 1.0
        assert ind.genes["coordination_weight"] == 1.0

    def test_individual_clamps_out_of_bounds_genes(self) -> None:
        """Verifies initializing with out-of-bounds values clamps strictly to authorized limits."""
        wild_genes = {
            "pawn_value": 99999,  # max is 120
            "knight_value": -500,  # min is 250
            "bishop_value": 330,
            "rook_value": 500,
            "queen_value": 900,
            "material_weight": 99.0,  # max is 1.5
            "pst_weight": -10.0,  # min is 0.2
            "mobility_weight": 1.0,
            "pawn_structure_weight": 1.0,
            "center_control_weight": 1.0,
            "king_safety_weight": 1.0,
            "coordination_weight": 1.0,
        }
        ind = Individual(genes=wild_genes)
        assert ind.genes["pawn_value"] == 120
        assert ind.genes["knight_value"] == 250
        assert ind.genes["material_weight"] == 1.5
        assert ind.genes["pst_weight"] == 0.2

    def test_individual_to_evaluation_config_conversion(self) -> None:
        """Verifies conversion to and from EvaluationConfig is exact and loss-free."""
        ind = Individual.create_baseline()
        cfg = ind.to_evaluation_config()
        assert isinstance(cfg, EvaluationConfig)
        assert cfg.pawn_value == ind.genes["pawn_value"]
        assert cfg.knight_value == ind.genes["knight_value"]
        assert cfg.material_weight == ind.genes["material_weight"]

        roundtrip = Individual.from_evaluation_config(cfg)
        assert roundtrip.genes == ind.genes

    def test_individual_validation_errors(self) -> None:
        """Verifies that missing genes or improper types raise ValueError during validation."""
        ind = Individual.create_baseline()
        del ind.genes["pawn_value"]
        with pytest.raises(ValueError, match="Missing required gene"):
            ind.validate()


class TestTuningDatasets:
    """Tests for dataset integrity, FEN validity, and strict train/val separation."""

    def test_training_and_validation_suites_strictly_disjoint(self) -> None:
        """Verifies no overlapping positions or FENs between training and held-out validation suites."""
        train = get_training_suite()
        val = get_validation_suite()

        assert len(train) >= 20
        assert len(val) >= 12

        train_ids = {p.id for p in train}
        val_ids = {p.id for p in val}
        assert train_ids.isdisjoint(val_ids), f"Overlapping IDs found: {train_ids & val_ids}"

        train_fens = {p.fen for p in train}
        val_fens = {p.fen for p in val}
        assert train_fens.isdisjoint(val_fens), f"Overlapping FENs found: {train_fens & val_fens}"

    def test_independent_suite_disjointness_and_validity(self) -> None:
        """Verifies independent suite has zero overlap with training/validation and has legal boards."""
        from engine.tuning import get_independent_suite
        train = get_training_suite()
        val = get_validation_suite()
        indep = get_independent_suite()

        assert len(indep) >= 6
        indep_ids = {p.id for p in indep}
        indep_fens = {p.fen for p in indep}

        assert indep_ids.isdisjoint({p.id for p in train})
        assert indep_ids.isdisjoint({p.id for p in val})
        assert indep_fens.isdisjoint({p.fen for p in train})
        assert indep_fens.isdisjoint({p.fen for p in val})

        for p in indep:
            board = chess.Board(p.fen)
            assert board.is_valid()
            if p.expected_best_move_uci:
                move = chess.Move.from_uci(p.expected_best_move_uci)
                assert board.is_legal(move)

    def test_all_dataset_positions_are_legal_chess_boards(self) -> None:
        """Verifies every position in both datasets parses as a legal, valid chess.Board."""
        for p in get_training_suite() + get_validation_suite():
            board = chess.Board(p.fen)
            assert board.is_valid(), f"Position {p.id} has invalid board state"
            if p.expected_best_move_uci:
                move = chess.Move.from_uci(p.expected_best_move_uci)
                assert board.is_legal(move), f"Position {p.id} best move {move} is illegal"


class TestGeneticOperators:
    """Tests for selection, crossover, mutation, and population operators."""

    def test_tournament_selection_picks_fittest(self) -> None:
        """Verifies tournament selection reliably picks highest-fitness contestant."""
        ind1 = Individual.create_baseline()
        ind1.fitness = 50.0
        ind2 = Individual.create_baseline()
        ind2.fitness = 90.0
        ind3 = Individual.create_baseline()
        ind3.fitness = 20.0

        winner = tournament_selection([ind1, ind2, ind3], tournament_size=3)
        assert winner is ind2

    def test_tournament_selection_validates_inputs(self) -> None:
        """Verifies error handling on empty population or invalid tournament size."""
        with pytest.raises(ValueError):
            tournament_selection([], tournament_size=2)
        with pytest.raises(ValueError):
            tournament_selection([Individual.create_baseline()], tournament_size=0)

    def test_rank_selection(self) -> None:
        """Verifies rank selection selects an individual from population."""
        pop = [Individual.create_baseline() for _ in range(5)]
        for i, ind in enumerate(pop):
            ind.fitness = float(i * 10)
        rng = random.Random(42)
        selected = rank_selection(pop, random_state=rng)
        assert selected in pop

    def test_blend_crossover_bounds_and_type_safety(self) -> None:
        """Verifies BLX-alpha crossover outputs valid offspring within gene boundaries."""
        p1 = Individual.create_baseline()
        p2 = Individual.create_baseline()
        p2.genes["pawn_value"] = 120
        p2.genes["material_weight"] = 1.4

        c1, c2 = blend_crossover(p1, p2, alpha=0.3, random_state=random.Random(42))
        assert c1.validate()
        assert c2.validate()
        assert c1.fitness is None
        assert c2.fitness is None

    def test_uniform_crossover(self) -> None:
        """Verifies uniform crossover creates valid offspring."""
        p1 = Individual.create_baseline()
        p2 = Individual.create_baseline()
        p2.genes["pawn_value"] = 85
        c1, c2 = uniform_crossover(p1, p2, swap_prob=0.5, random_state=random.Random(42))
        assert c1.validate()
        assert c2.validate()

    def test_mutate_individual_stays_within_bounds(self) -> None:
        """Verifies aggressive mutation rate never breaches GeneSpec min/max limits."""
        ind = Individual.create_baseline()
        ind.fitness = 85.0
        rng = random.Random(123)

        for _ in range(10):
            mutate_individual(ind, mutation_rate=1.0, mutation_magnitude=0.5, random_state=rng)
            assert ind.validate()
            assert ind.fitness is None


class TestPopulationAndElitism:
    """Tests for population generation, elitism, and statistical summaries."""

    def test_population_create_initial_contains_baseline(self) -> None:
        """Verifies generation 0 initial population starts with exact engine baseline."""
        pop = Population.create_initial(population_size=6, random_state=random.Random(42))
        assert len(pop) == 6
        assert pop.generation == 0

        base_ind = Individual.create_baseline()
        assert pop[0].genes == base_ind.genes

    def test_population_get_best_and_elites(self) -> None:
        """Verifies extraction of best individual and top-K elites preserving fitness."""
        pop = Population.create_initial(population_size=4, random_state=random.Random(42))
        for i, ind in enumerate(pop):
            ind.fitness = float(i * 10 + 50)

        best = pop.get_best()
        assert best.fitness == 80.0

        elites = pop.get_elites(count=2)
        assert len(elites) == 2
        assert elites[0].fitness == 80.0
        assert elites[1].fitness == 70.0

    def test_population_statistics(self) -> None:
        """Verifies mean, best, std, and diversity calculations."""
        pop = Population.create_initial(population_size=4, random_state=random.Random(42))
        for i, ind in enumerate(pop):
            ind.fitness = float(70 + i * 10)

        stats = pop.statistics()
        assert stats["best_fitness"] == 100.0
        assert stats["min_fitness"] == 70.0
        assert stats["mean_fitness"] == 85.0
        assert stats["diversity"] >= 0.0


class TestFitnessEvaluator:
    """Tests for multi-objective fitness evaluation and symmetry checking."""

    def test_fitness_config_validation(self) -> None:
        """Verifies FitnessConfig requires weights summing to 1.0."""
        with pytest.raises(ValueError, match="Fitness weights must sum to 1.0"):
            FitnessConfig(positional_weight=0.5, tactical_weight=0.2, symmetry_weight=0.1)

    def test_baseline_fitness_evaluation(self) -> None:
        """Verifies baseline individual scores high fitness with full breakdown."""
        evaluator = FitnessEvaluator()
        baseline = Individual.create_baseline()
        fitness = evaluator.evaluate(baseline)

        assert 80.0 <= fitness <= 100.0
        assert baseline.fitness_breakdown is not None
        assert "positional_score" in baseline.fitness_breakdown
        assert "tactical_score" in baseline.fitness_breakdown
        assert "symmetry_score" in baseline.fitness_breakdown
        assert baseline.fitness_breakdown["symmetry_score"] == 100.0

    def test_validation_evaluation_does_not_mutate_individual(self) -> None:
        """Verifies held-out validation evaluation leaves individual fitness untouched."""
        evaluator = FitnessEvaluator()
        ind = Individual.create_baseline()
        ind.fitness = 42.0

        val_metrics = evaluator.evaluate_validation(ind)
        assert ind.fitness == 42.0
        assert "validation_fitness" in val_metrics
        assert val_metrics["validation_fitness"] >= 80.0


class TestGeneticAlgorithmExecution:
    """Tests for full optimizer execution, dry-run, reproducibility, and export."""

    def test_ga_dry_run_mode(self) -> None:
        """Verifies dry-run mode evaluates Generation 0 and terminates immediately."""
        config = GAConfig(generations=10, population_size=4, dry_run=True, random_seed=42)
        optimizer = GeneticAlgorithm(config=config)
        result = optimizer.run()

        assert result.total_generations == 1
        assert len(result.history) == 1
        assert result.history[0].generation == 0

    def test_ga_deterministic_reproducibility(self) -> None:
        """Verifies identical random seeds produce byte-for-byte identical optimization runs."""
        cfg1 = GAConfig(generations=2, population_size=4, random_seed=999)
        res1 = GeneticAlgorithm(config=cfg1).run()

        cfg2 = GAConfig(generations=2, population_size=4, random_seed=999)
        res2 = GeneticAlgorithm(config=cfg2).run()

        assert res1.best_fitness == res2.best_fitness
        assert res1.best_individual.genes == res2.best_individual.genes
        assert res1.history[0].best_fitness == res2.history[0].best_fitness

    def test_ga_export_and_load_config(self, tmp_path: Path) -> None:
        """Verifies exported JSON configuration can be loaded into an EvaluationConfig."""
        config = GAConfig(generations=2, population_size=4, random_seed=42)
        result = GeneticAlgorithm(config=config).run()

        json_path = tmp_path / "test_tuned_weights.json"
        result.export_tuned_config(str(json_path))

        assert json_path.is_file()
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["metadata"]["format_version"] == "1.0"
        assert "genes" in data
        assert len(data["genes"]) == 12

        loaded_config = GAResult.load_tuned_config(str(json_path))
        assert isinstance(loaded_config, EvaluationConfig)
        assert loaded_config.pawn_value == result.best_individual.genes["pawn_value"]

        # Verify loaded config can be passed to the engine's evaluate_position
        board = chess.Board()
        score = evaluate_position(board, config=loaded_config)
        assert isinstance(score, int)

    def test_ga_early_stopping(self) -> None:
        """Verifies early stopping halts evolution when no improvement occurs."""
        config = GAConfig(
            generations=15,
            population_size=4,
            early_stopping_generations=2,
            mutation_magnitude=0.001,
            random_seed=42,
        )
        result = GeneticAlgorithm(config=config).run()
        assert result.total_generations < 15


class TestTuningEdgeCasesAndCoverage:
    """Additional edge cases ensuring >98% coverage across all tuning submodules."""

    def test_individual_repr_and_dict_serialization(self) -> None:
        """Verifies Individual string formatting and roundtrip dict serialization."""
        ind = Individual.create_baseline()
        ind.fitness = 95.5
        ind.fitness_breakdown = {"total_fitness": 95.5}

        repr_str = repr(ind)
        assert "fitness=95.50" in repr_str
        assert "genes=" in repr_str

        data = ind.to_dict()
        assert data["fitness"] == 95.5
        assert data["genes"]["pawn_value"] == 100

        restored = Individual.from_dict(data)
        assert restored.fitness == 95.5
        assert restored.genes == ind.genes

    def test_individual_validation_type_and_bound_checks(self) -> None:
        """Verifies type checks and bounds checks in individual.validate()."""
        ind = Individual.create_baseline()
        ind.genes["pawn_value"] = "invalid_type"  # type: ignore
        with pytest.raises(ValueError, match="must be int"):
            ind.validate()

        ind2 = Individual.create_baseline()
        ind2.genes["material_weight"] = "invalid_float"  # type: ignore
        with pytest.raises(ValueError, match="must be float"):
            ind2.validate()

        ind3 = Individual.create_baseline()
        ind3.genes["knight_value"] = 9999
        with pytest.raises(ValueError, match="outside bounds"):
            ind3.validate()

    def test_individual_clamp_missing_gene(self) -> None:
        """Verifies clamp_genes resets missing genes to baseline defaults."""
        genes = {"pawn_value": 100}
        ind = Individual(genes=genes)
        assert "knight_value" in ind.genes
        assert ind.genes["knight_value"] == DEFAULT_KNIGHT_VALUE

    def test_population_error_handling(self) -> None:
        """Verifies population initialization and elite extraction edge cases."""
        with pytest.raises(ValueError, match="must have at least 2"):
            Population(individuals=[Individual.create_baseline()])

        with pytest.raises(ValueError, match="population_size must be >= 2"):
            Population.create_initial(population_size=1)

        pop = Population(individuals=[Individual.create_baseline(), Individual.create_baseline()])
        with pytest.raises(ValueError, match="No individuals in population have evaluated fitness"):
            pop.get_best()

        assert pop.get_elites(count=0) == []
        stats = pop.statistics()
        assert stats["best_fitness"] == 0.0

    def test_selection_edge_cases(self) -> None:
        """Verifies edge cases in rank and tournament selection."""
        ind = Individual.create_baseline()
        ind.fitness = 80.0
        # Single individual in rank selection returns it directly
        assert rank_selection([ind]) is ind

        with pytest.raises(ValueError):
            rank_selection([])

    def test_ga_config_validation_errors(self) -> None:
        """Verifies GAConfig post-init parameter validation."""
        with pytest.raises(ValueError, match="generations must be >= 1"):
            GAConfig(generations=0)

        with pytest.raises(ValueError, match="population_size must be >= 2"):
            GAConfig(population_size=1)

        with pytest.raises(ValueError, match="elite_count must be between 0 and population_size - 1"):
            GAConfig(population_size=4, elite_count=4)

        with pytest.raises(ValueError, match="crossover_rate must be between 0 and 1"):
            GAConfig(crossover_rate=-0.1)

        with pytest.raises(ValueError, match="mutation_rate must be between 0 and 1"):
            GAConfig(mutation_rate=1.5)

    def test_results_serialization_and_errors(self) -> None:
        """Verifies GAResult serialization and file loading errors."""
        with pytest.raises(FileNotFoundError):
            GAResult.load_tuned_config("non_existent_path.json")

        cfg = GAConfig(generations=1, population_size=4, dry_run=True, random_seed=42)
        res = GeneticAlgorithm(config=cfg).run()
        d = res.to_dict()
        assert "baseline_fitness" in d
        assert "history" in d

    def test_ga_dry_run_with_callback(self) -> None:
        """Verifies dry-run triggers progress callback on Generation 0."""
        calls = []
        cfg = GAConfig(
            generations=5,
            population_size=4,
            dry_run=True,
            random_seed=42,
            progress_callback=lambda t: calls.append(t.generation),
        )
        GeneticAlgorithm(config=cfg).run()
        assert calls == [0]

    def test_fitness_evaluator_edge_cases(self) -> None:
        """Verifies evaluator behavior on empty or custom datasets."""
        evaluator = FitnessEvaluator(
            config=FitnessConfig(symmetry_sample_size=0),
            dataset=[],
        )
        ind = Individual.create_baseline()
        score = evaluator.evaluate(ind)
        assert score >= 0.0

        val_metrics = evaluator.evaluate_validation(ind, validation_suite=[])
        assert val_metrics["positional_total"] == 0
        assert val_metrics["tactical_total"] == 0
