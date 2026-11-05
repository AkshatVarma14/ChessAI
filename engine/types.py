"""Data structures and types for engine search and evaluation."""

from dataclasses import dataclass, field
from typing import List, Optional
import chess


@dataclass(frozen=True)
class EvaluationBreakdown:
    """Detailed component breakdown of static position evaluation."""

    white_material: int
    black_material: int
    material_cp: int
    total_cp: int
    is_terminal: bool
    pst_cp: int = 0
    mobility_cp: int = 0
    pawn_structure_cp: int = 0
    center_control_cp: int = 0
    king_safety_cp: int = 0
    coordination_cp: int = 0
    game_phase: float = 1.0
    terminal_type: Optional[str] = None


@dataclass(frozen=True)
class SearchResult:
    """Structured result of an adversarial move search."""

    best_move: Optional[chess.Move]
    best_move_uci: Optional[str]
    best_move_san: Optional[str]
    score_cp: int
    depth: int
    nodes_searched: int
    pruned_nodes: int
    elapsed_ms: float
    nodes_per_second: int
    algorithm: str
    quiescence_nodes: int = 0
    tt_probes: int = 0
    tt_hits: int = 0
    tt_cutoffs: int = 0
    tt_stores: int = 0
    is_checkmate: bool = False
    is_draw: bool = False
    completed_depth: Optional[int] = None
    is_interrupted: bool = False
    interruption_reason: Optional[str] = None
    allocated_time_ms: Optional[float] = None
    difficulty: Optional[str] = None
    pv_uci: List[str] = field(default_factory=list)
    pv_san: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Default completed_depth to depth if not explicitly specified."""
        if self.completed_depth is None:
            object.__setattr__(self, "completed_depth", self.depth)
