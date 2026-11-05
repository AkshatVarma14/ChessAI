"""Multi-objective fitness evaluator for the Genetic Algorithm.

Computes fitness for candidate Individuals based on:
1. Positional Advantage Alignment: Agreement with curated ground-truth strategic evaluations.
2. Tactical Decision Quality: Accuracy in executing tactical wins and avoiding blunders.
3. Evaluation Symmetry: Invariant preservation under color and board mirroring.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import chess

from engine.evaluation.evaluator import evaluate_position
from engine.search.alpha_beta import alpha_beta_search
from engine.tuning.dataset import TuningPosition, get_training_suite, get_validation_suite
from engine.tuning.individual import Individual


@dataclass(frozen=True)
class FitnessConfig:
    """
    Configuration parameters for multi-objective fitness evaluation.

    Attributes:
        positional_weight: Proportion of fitness derived from static evaluation alignment (0.0 to 1.0).
        tactical_weight: Proportion of fitness derived from tactical move quality (0.0 to 1.0).
        symmetry_weight: Proportion of fitness derived from mirrored evaluation symmetry (0.0 to 1.0).
        tactical_depth: Search depth for tactical move verification (default: 1 for fast evaluation).
        symmetry_sample_size: Number of positions sampled to check evaluation symmetry.
    """

    positional_weight: float = 0.60
    tactical_weight: float = 0.35
    symmetry_weight: float = 0.05
    tactical_depth: int = 1
    symmetry_sample_size: int = 4

    def __post_init__(self) -> None:
        total = self.positional_weight + self.tactical_weight + self.symmetry_weight
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Fitness weights must sum to 1.0, got {total}")


class FitnessEvaluator:
    """
    Evaluates individual fitness against curated chess positions.

    Maintains clean separation between training evaluations and held-out validation.
    """

    def __init__(
        self,
        config: Optional[FitnessConfig] = None,
        dataset: Optional[List[TuningPosition]] = None,
    ) -> None:
        """
        Initializes the fitness evaluator.

        Args:
            config: Optional fitness weight configuration.
            dataset: Custom training dataset; defaults to the authoritative training suite.
        """
        self.config = config or FitnessConfig()
        self.dataset = list(dataset) if dataset is not None else get_training_suite()

    def evaluate(self, individual: Individual) -> float:
        """
        Computes multi-objective fitness score for an individual.

        Mutates individual.fitness and individual.fitness_breakdown.

        Args:
            individual: The candidate Individual to evaluate.

        Returns:
            Composite fitness score between 0.0 and 100.0.
        """
        eval_config = individual.to_evaluation_config()

        # 1. Positional Advantage Alignment Score
        pos_score, pos_correct, pos_total = self._evaluate_positional(eval_config)

        # 2. Tactical Decision Quality Score
        tac_score, tac_correct, tac_total = self._evaluate_tactical(eval_config)

        # 3. Evaluation Symmetry Score
        sym_score = self._evaluate_symmetry(eval_config)

        # Composite weighted score
        composite = (
            self.config.positional_weight * pos_score
            + self.config.tactical_weight * tac_score
            + self.config.symmetry_weight * sym_score
        )
        composite = max(0.0, min(100.0, round(composite, 4)))

        pos_accuracy = (pos_correct / pos_total * 100.0) if pos_total > 0 else 0.0
        tac_accuracy = (tac_correct / tac_total * 100.0) if tac_total > 0 else 0.0

        individual.fitness = composite
        individual.fitness_breakdown = {
            "positional_score": round(pos_score, 2),
            "tactical_score": round(tac_score, 2),
            "symmetry_score": round(sym_score, 2),
            "total_fitness": composite,
            "positional_accuracy": round(pos_accuracy, 2),
            "tactical_accuracy": round(tac_accuracy, 2),
            "positional_positions_evaluated": float(pos_total),
            "tactical_positions_evaluated": float(tac_total),
        }

        return composite

    def evaluate_validation(
        self,
        individual: Individual,
        validation_suite: Optional[List[TuningPosition]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates an individual against the held-out validation suite.

        Does NOT mutate individual.fitness or individual.fitness_breakdown.

        Args:
            individual: Candidate Individual to evaluate.
            validation_suite: Optional held-out validation positions.

        Returns:
            Dictionary containing validation performance metrics.
        """
        val_suite = validation_suite if validation_suite is not None else get_validation_suite()
        eval_config = individual.to_evaluation_config()

        pos_weighted_sum = 0.0
        pos_weight_total = 0.0
        pos_correct = 0
        pos_total = 0

        tac_weighted_sum = 0.0
        tac_weight_total = 0.0
        tac_correct = 0
        tac_total = 0

        for pos in val_suite:
            board = chess.Board(pos.fen)

            # Positional static evaluation check
            if pos.expected_eval_sign is not None:
                score = evaluate_position(board, config=eval_config)
                ratio, matched = self._score_positional_result(score, pos)
                pos_weighted_sum += ratio * pos.weight
                pos_weight_total += pos.weight
                pos_total += 1
                if matched:
                    pos_correct += 1

            # Tactical check
            if pos.expected_best_move_uci or pos.avoid_move_uci:
                result = alpha_beta_search(
                    board,
                    depth=self.config.tactical_depth,
                    config=eval_config,
                    use_quiescence=False,
                    use_transposition_table=False,
                )
                chosen_uci = result.best_move.uci() if result.best_move else ""
                matched = False
                if pos.expected_best_move_uci and chosen_uci == pos.expected_best_move_uci:
                    matched = True
                elif pos.avoid_move_uci and chosen_uci != pos.avoid_move_uci:
                    matched = True

                ratio = 1.0 if matched else 0.0
                tac_weighted_sum += ratio * pos.weight
                tac_weight_total += pos.weight
                tac_total += 1
                if matched:
                    tac_correct += 1

        val_pos_score = (pos_weighted_sum / pos_weight_total * 100.0) if pos_weight_total > 0 else 0.0
        val_tac_score = (tac_weighted_sum / tac_weight_total * 100.0) if tac_weight_total > 0 else 0.0
        pos_acc = (pos_correct / pos_total * 100.0) if pos_total > 0 else 0.0
        tac_acc = (tac_correct / tac_total * 100.0) if tac_total > 0 else 0.0

        val_composite = (
            self.config.positional_weight * val_pos_score
            + self.config.tactical_weight * val_tac_score
            + self.config.symmetry_weight * 100.0
        )

        return {
            "validation_fitness": round(val_composite, 4),
            "positional_score": round(val_pos_score, 2),
            "tactical_score": round(val_tac_score, 2),
            "positional_accuracy": round(pos_acc, 2),
            "tactical_accuracy": round(tac_acc, 2),
            "positional_correct": pos_correct,
            "positional_total": pos_total,
            "tactical_correct": tac_correct,
            "tactical_total": tac_total,
        }

    def _evaluate_positional(self, eval_config: Any) -> tuple[float, int, int]:
        """Evaluates positional static evaluation alignment across dataset positions."""
        weighted_sum = 0.0
        weight_total = 0.0
        correct_count = 0
        total_count = 0

        for pos in self.dataset:
            if pos.expected_eval_sign is None:
                continue

            board = chess.Board(pos.fen)
            score = evaluate_position(board, config=eval_config)
            ratio, matched = self._score_positional_result(score, pos)

            weighted_sum += ratio * pos.weight
            weight_total += pos.weight
            total_count += 1
            if matched:
                correct_count += 1

        score_pct = (weighted_sum / weight_total * 100.0) if weight_total > 0 else 0.0
        return score_pct, correct_count, total_count

    def _score_positional_result(self, score: int, pos: TuningPosition) -> tuple[float, bool]:
        """Calculates normalized reward ratio and binary match status for a positional score."""
        target_margin = pos.min_expected_margin_cp or 0

        if pos.expected_eval_sign == 1:
            if score > 0:
                if target_margin > 0:
                    margin_ratio = min(1.0, score / target_margin)
                    reward = 0.60 + 0.40 * margin_ratio
                else:
                    reward = 1.0
                return reward, True
            return 0.0, False

        elif pos.expected_eval_sign == -1:
            if score < 0:
                if target_margin < 0:
                    margin_ratio = min(1.0, score / target_margin)  # both negative, ratio positive
                    reward = 0.60 + 0.40 * margin_ratio
                else:
                    reward = 1.0
                return reward, True
            return 0.0, False

        else:  # expected_eval_sign == 0 (balanced)
            abs_score = abs(score)
            if abs_score <= 40:
                return 1.0, True
            elif abs_score <= 100:
                ratio = max(0.0, 1.0 - (abs_score - 40) / 60.0)
                return ratio, True
            return 0.0, False

    def _evaluate_tactical(self, eval_config: Any) -> tuple[float, int, int]:
        """Evaluates tactical move accuracy across dataset positions with expected moves."""
        weighted_sum = 0.0
        weight_total = 0.0
        correct_count = 0
        total_count = 0

        for pos in self.dataset:
            if not pos.expected_best_move_uci and not pos.avoid_move_uci:
                continue

            board = chess.Board(pos.fen)
            result = alpha_beta_search(
                board,
                depth=self.config.tactical_depth,
                config=eval_config,
                use_quiescence=False,
                use_transposition_table=False,
            )
            chosen_uci = result.best_move.uci() if result.best_move else ""
            matched = False

            if pos.expected_best_move_uci and chosen_uci == pos.expected_best_move_uci:
                matched = True
            elif pos.avoid_move_uci and chosen_uci != pos.avoid_move_uci:
                matched = True

            ratio = 1.0 if matched else 0.0
            weighted_sum += ratio * pos.weight
            weight_total += pos.weight
            total_count += 1
            if matched:
                correct_count += 1

        score_pct = (weighted_sum / weight_total * 100.0) if weight_total > 0 else 0.0
        return score_pct, correct_count, total_count

    def _evaluate_symmetry(self, eval_config: Any) -> float:
        """Verifies board evaluation symmetry: E(pos) == -E(pos.mirror())."""
        sample_count = min(self.config.symmetry_sample_size, len(self.dataset))
        if sample_count == 0:
            return 100.0

        errors: List[float] = []
        for i in range(sample_count):
            board = chess.Board(self.dataset[i].fen)
            mirrored = board.mirror()
            s1 = evaluate_position(board, config=eval_config)
            s2 = evaluate_position(mirrored, config=eval_config)
            error = abs(s1 + s2)
            errors.append(error)

        avg_error = sum(errors) / len(errors)
        if avg_error == 0:
            return 100.0
        return max(0.0, 100.0 - avg_error)
