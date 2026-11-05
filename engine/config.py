"""Configuration dataclasses for chess engine search and evaluation."""

from dataclasses import dataclass
from typing import Literal, Optional
import chess

from engine.constants import (
    DEFAULT_BISHOP_VALUE,
    DEFAULT_KNIGHT_VALUE,
    DEFAULT_PAWN_VALUE,
    DEFAULT_QUEEN_VALUE,
    DEFAULT_ROOK_VALUE,
)

SearchAlgorithm = Literal["minimax", "alpha_beta", "iterative_deepening"]


@dataclass(frozen=True)
class EvaluationConfig:
    """Configurable weights and piece values for static position evaluation."""

    pawn_value: int = DEFAULT_PAWN_VALUE
    knight_value: int = DEFAULT_KNIGHT_VALUE
    bishop_value: int = DEFAULT_BISHOP_VALUE
    rook_value: int = DEFAULT_ROOK_VALUE
    queen_value: int = DEFAULT_QUEEN_VALUE

    # Component weights (multiplier >= 0.0)
    material_weight: float = 1.0
    pst_weight: float = 1.0
    mobility_weight: float = 1.0
    pawn_structure_weight: float = 1.0
    center_control_weight: float = 1.0
    king_safety_weight: float = 1.0
    coordination_weight: float = 1.0

    # Component feature toggles
    use_pst: bool = True
    use_mobility: bool = True
    use_pawn_structure: bool = True
    use_center_control: bool = True
    use_king_safety: bool = True
    use_coordination: bool = True

    def __post_init__(self) -> None:
        """Validate that all piece values and component weights are non-negative."""
        for name in ("pawn_value", "knight_value", "bishop_value", "rook_value", "queen_value"):
            val = getattr(self, name)
            if not isinstance(val, int) or val <= 0:
                raise ValueError(f"{name} must be a positive integer, got {val}")

        for w_name in (
            "material_weight",
            "pst_weight",
            "mobility_weight",
            "pawn_structure_weight",
            "center_control_weight",
            "king_safety_weight",
            "coordination_weight",
        ):
            w_val = getattr(self, w_name)
            if not isinstance(w_val, (int, float)) or w_val < 0.0:
                raise ValueError(f"{w_name} must be a non-negative number, got {w_val}")

    def get_piece_value(self, piece_type: chess.PieceType) -> int:
        """Look up the configured centipawn value for a standard piece type."""
        match piece_type:
            case chess.PAWN:
                return self.pawn_value
            case chess.KNIGHT:
                return self.knight_value
            case chess.BISHOP:
                return self.bishop_value
            case chess.ROOK:
                return self.rook_value
            case chess.QUEEN:
                return self.queen_value
            case chess.KING:
                return 0
            case _:
                return 0


@dataclass(frozen=True)
class SearchConfig:
    """Configuration for adversarial search execution."""

    depth: int = 3
    algorithm: SearchAlgorithm = "alpha_beta"
    time_limit_ms: Optional[float] = None
    max_nodes: Optional[int] = None
    use_iterative_deepening: bool = False
    use_move_ordering: bool = True
    use_quiescence: bool = True
    max_quiescence_depth: int = 8
    max_check_depth: int = 2
    use_transposition_table: bool = True
    transposition_table_size_mb: int = 16

    def __post_init__(self) -> None:
        """Validate search bounds, budgets, and algorithm choices."""
        if not isinstance(self.depth, int) or self.depth < 1:
            raise ValueError(f"Search depth must be an integer >= 1, got {self.depth}")
        if self.algorithm not in ("minimax", "alpha_beta", "iterative_deepening"):
            raise ValueError(f"Unknown search algorithm: '{self.algorithm}'")
        if self.time_limit_ms is not None and (
            not isinstance(self.time_limit_ms, (int, float)) or self.time_limit_ms <= 0
        ):
            raise ValueError(f"time_limit_ms must be a positive number, got {self.time_limit_ms}")
        if self.max_nodes is not None and (not isinstance(self.max_nodes, int) or self.max_nodes < 1):
            raise ValueError(f"max_nodes must be an integer >= 1, got {self.max_nodes}")
        if not isinstance(self.max_quiescence_depth, int) or self.max_quiescence_depth < 0:
            raise ValueError(f"max_quiescence_depth must be an integer >= 0, got {self.max_quiescence_depth}")
        if not isinstance(self.max_check_depth, int) or self.max_check_depth < 0:
            raise ValueError(f"max_check_depth must be an integer >= 0, got {self.max_check_depth}")
        if not isinstance(self.transposition_table_size_mb, int) or self.transposition_table_size_mb < 1:
            raise ValueError(f"transposition_table_size_mb must be an integer >= 1, got {self.transposition_table_size_mb}")
