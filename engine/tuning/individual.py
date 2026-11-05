"""Individual representation and gene specifications for evaluation weight tuning.

Represents an individual in the Genetic Algorithm population as a set of bounded
evaluation weights mapping directly to the chess engine's EvaluationConfig.
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from engine.config import EvaluationConfig
from engine.constants import (
    DEFAULT_BISHOP_VALUE,
    DEFAULT_KNIGHT_VALUE,
    DEFAULT_PAWN_VALUE,
    DEFAULT_QUEEN_VALUE,
    DEFAULT_ROOK_VALUE,
)


@dataclass(frozen=True)
class GeneSpec:
    """
    Specification for a single tunable gene.

    Attributes:
        name: Name of the configuration parameter matching EvaluationConfig.
        gene_type: Type of gene (int or float).
        baseline: Handcrafted default value.
        min_value: Strict lower boundary.
        max_value: Strict upper boundary.
        description: Description of the evaluation feature controlled by this gene.
    """

    name: str
    gene_type: type
    baseline: Union[int, float]
    min_value: Union[int, float]
    max_value: Union[int, float]
    description: str


# Authoritative gene definitions for all 12 tunable EvaluationConfig parameters.
GENE_SPECS: Tuple[GeneSpec, ...] = (
    GeneSpec(
        name="pawn_value",
        gene_type=int,
        baseline=DEFAULT_PAWN_VALUE,
        min_value=80,
        max_value=120,
        description="Centipawn valuation of a pawn",
    ),
    GeneSpec(
        name="knight_value",
        gene_type=int,
        baseline=DEFAULT_KNIGHT_VALUE,
        min_value=250,
        max_value=400,
        description="Centipawn valuation of a knight",
    ),
    GeneSpec(
        name="bishop_value",
        gene_type=int,
        baseline=DEFAULT_BISHOP_VALUE,
        min_value=260,
        max_value=420,
        description="Centipawn valuation of a bishop",
    ),
    GeneSpec(
        name="rook_value",
        gene_type=int,
        baseline=DEFAULT_ROOK_VALUE,
        min_value=420,
        max_value=600,
        description="Centipawn valuation of a rook",
    ),
    GeneSpec(
        name="queen_value",
        gene_type=int,
        baseline=DEFAULT_QUEEN_VALUE,
        min_value=800,
        max_value=1150,
        description="Centipawn valuation of a queen",
    ),
    GeneSpec(
        name="material_weight",
        gene_type=float,
        baseline=1.0,
        min_value=0.50,
        max_value=1.50,
        description="Multiplier for total material balance",
    ),
    GeneSpec(
        name="pst_weight",
        gene_type=float,
        baseline=1.0,
        min_value=0.20,
        max_value=2.50,
        description="Multiplier for piece-square table positional scores",
    ),
    GeneSpec(
        name="mobility_weight",
        gene_type=float,
        baseline=1.0,
        min_value=0.20,
        max_value=2.50,
        description="Multiplier for piece mobility terms",
    ),
    GeneSpec(
        name="pawn_structure_weight",
        gene_type=float,
        baseline=1.0,
        min_value=0.20,
        max_value=2.50,
        description="Multiplier for passed, isolated, and doubled pawn evaluations",
    ),
    GeneSpec(
        name="center_control_weight",
        gene_type=float,
        baseline=1.0,
        min_value=0.20,
        max_value=2.50,
        description="Multiplier for central square occupation and attack control",
    ),
    GeneSpec(
        name="king_safety_weight",
        gene_type=float,
        baseline=1.0,
        min_value=0.20,
        max_value=2.50,
        description="Multiplier for king pawn shield and zone safety terms",
    ),
    GeneSpec(
        name="coordination_weight",
        gene_type=float,
        baseline=1.0,
        min_value=0.20,
        max_value=2.50,
        description="Multiplier for bishop pair, open files, and 7th rank piece coordination",
    ),
)

GENE_MAP: Dict[str, GeneSpec] = {spec.name: spec for spec in GENE_SPECS}


class Individual:
    """
    Candidate individual in the Genetic Algorithm.

    Encapsulates a complete chromosome of evaluation weights, provides conversion
    to/from the engine's EvaluationConfig, and enforces hard parameter bounds.
    """

    def __init__(
        self,
        genes: Optional[Dict[str, Union[int, float]]] = None,
        fitness: Optional[float] = None,
        fitness_breakdown: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Initializes an Individual with the provided genes or baseline defaults.

        Args:
            genes: Mapping of gene names to parameter values.
            fitness: Evaluated fitness score (higher is better).
            fitness_breakdown: Detailed component scores contributing to fitness.
        """
        if genes is None:
            self.genes: Dict[str, Union[int, float]] = {
                spec.name: spec.baseline for spec in GENE_SPECS
            }
        else:
            self.genes = dict(genes)

        self.fitness: Optional[float] = fitness
        self.fitness_breakdown: Optional[Dict[str, float]] = (
            dict(fitness_breakdown) if fitness_breakdown is not None else None
        )
        self.clamp_genes()

    def clamp_genes(self) -> None:
        """Clamps all gene values strictly within their authorized GeneSpec ranges."""
        for name, spec in GENE_MAP.items():
            if name not in self.genes:
                self.genes[name] = spec.baseline
            val = self.genes[name]
            clamped = max(spec.min_value, min(spec.max_value, val))
            if spec.gene_type is int:
                self.genes[name] = int(round(clamped))
            else:
                self.genes[name] = round(float(clamped), 4)

    def validate(self) -> bool:
        """
        Validates that all expected genes are present, correctly typed, and within bounds.

        Returns:
            True if all genes strictly conform to specifications.

        Raises:
            ValueError: If any gene is missing, incorrectly typed, or out of bounds.
        """
        for spec in GENE_SPECS:
            if spec.name not in self.genes:
                raise ValueError(f"Missing required gene: '{spec.name}'")
            val = self.genes[spec.name]
            if spec.gene_type is int and not isinstance(val, int):
                raise ValueError(
                    f"Gene '{spec.name}' must be int, got {type(val).__name__} ({val})"
                )
            if spec.gene_type is float and not isinstance(val, (int, float)):
                raise ValueError(
                    f"Gene '{spec.name}' must be float, got {type(val).__name__} ({val})"
                )
            if val < spec.min_value or val > spec.max_value:
                raise ValueError(
                    f"Gene '{spec.name}' value {val} outside bounds [{spec.min_value}, {spec.max_value}]"
                )
        return True

    def to_evaluation_config(self) -> EvaluationConfig:
        """
        Converts the individual's genes into an immutable EvaluationConfig instance.

        Returns:
            Ready-to-use EvaluationConfig for the custom chess engine.
        """
        self.validate()
        return EvaluationConfig(
            pawn_value=int(self.genes["pawn_value"]),
            knight_value=int(self.genes["knight_value"]),
            bishop_value=int(self.genes["bishop_value"]),
            rook_value=int(self.genes["rook_value"]),
            queen_value=int(self.genes["queen_value"]),
            material_weight=float(self.genes["material_weight"]),
            pst_weight=float(self.genes["pst_weight"]),
            mobility_weight=float(self.genes["mobility_weight"]),
            pawn_structure_weight=float(self.genes["pawn_structure_weight"]),
            center_control_weight=float(self.genes["center_control_weight"]),
            king_safety_weight=float(self.genes["king_safety_weight"]),
            coordination_weight=float(self.genes["coordination_weight"]),
        )

    @classmethod
    def from_evaluation_config(
        cls, config: EvaluationConfig, fitness: Optional[float] = None
    ) -> "Individual":
        """
        Constructs an Individual from an existing EvaluationConfig instance.

        Args:
            config: Source EvaluationConfig instance.
            fitness: Optional precomputed fitness score.

        Returns:
            New Individual initialized with the config's parameter values.
        """
        genes: Dict[str, Union[int, float]] = {
            "pawn_value": config.pawn_value,
            "knight_value": config.knight_value,
            "bishop_value": config.bishop_value,
            "rook_value": config.rook_value,
            "queen_value": config.queen_value,
            "material_weight": config.material_weight,
            "pst_weight": config.pst_weight,
            "mobility_weight": config.mobility_weight,
            "pawn_structure_weight": config.pawn_structure_weight,
            "center_control_weight": config.center_control_weight,
            "king_safety_weight": config.king_safety_weight,
            "coordination_weight": config.coordination_weight,
        }
        return cls(genes=genes, fitness=fitness)

    @classmethod
    def create_baseline(cls) -> "Individual":
        """Creates the canonical baseline individual using handcrafted engine defaults."""
        return cls()

    def clone(self) -> "Individual":
        """Creates a deep copy of this individual, including fitness and breakdown."""
        return Individual(
            genes=deepcopy(self.genes),
            fitness=self.fitness,
            fitness_breakdown=deepcopy(self.fitness_breakdown),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes individual to a JSON-compatible dictionary."""
        return {
            "genes": {k: v for k, v in self.genes.items()},
            "fitness": self.fitness,
            "fitness_breakdown": self.fitness_breakdown,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Individual":
        """Deserializes individual from a dictionary."""
        genes = data.get("genes", {})
        fitness = data.get("fitness")
        breakdown = data.get("fitness_breakdown")
        return cls(genes=genes, fitness=fitness, fitness_breakdown=breakdown)

    def __repr__(self) -> str:
        fit_str = f"{self.fitness:.2f}" if self.fitness is not None else "None"
        return f"Individual(fitness={fit_str}, genes={self.genes})"
