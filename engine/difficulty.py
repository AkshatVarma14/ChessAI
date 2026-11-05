"""Authoritative Difficulty Levels and Profiles for the Chess Engine.

Defines five named difficulty presets (Beginner, Easy, Medium, Hard, Expert)
as genuine configurations of the existing custom search engine.
No artificial random blunders are injected; difficulty scaling is achieved through
principled bounds on search depth, node budgets, time allocations, quiescence search,
move ordering heuristics, and transposition table caching.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Union

from engine.config import SearchConfig


class DifficultyLevel(str, Enum):
    """Supported difficulty levels for the chess engine."""

    BEGINNER = "beginner"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


@dataclass(frozen=True)
class DifficultyProfile:
    """
    Immutable specification of engine search parameters and time budgets for a difficulty level.
    
    Attributes:
        level: Named DifficultyLevel enum.
        display_name: Human-friendly name for UI rendering.
        description: Concise technical summary of the profile's capabilities.
        search_config: Configured SearchConfig instance tailored to this difficulty.
        base_time_ms: Default time budget allocation in milliseconds for a normal turn.
        max_time_ms: Hard upper limit on time allocation in milliseconds under tactical tension.
        min_time_ms: Minimum time budget in milliseconds for trivial/forced positions.
    """

    level: DifficultyLevel
    display_name: str
    description: str
    search_config: SearchConfig
    base_time_ms: float
    max_time_ms: float
    min_time_ms: float = 50.0

    def __post_init__(self) -> None:
        """Validate time budget relationships."""
        if self.min_time_ms <= 0:
            raise ValueError(f"min_time_ms must be positive, got {self.min_time_ms}")
        if self.base_time_ms < self.min_time_ms:
            raise ValueError(
                f"base_time_ms ({self.base_time_ms}) cannot be less than min_time_ms ({self.min_time_ms})"
            )
        if self.max_time_ms < self.base_time_ms:
            raise ValueError(
                f"max_time_ms ({self.max_time_ms}) cannot be less than base_time_ms ({self.base_time_ms})"
            )


# Authoritative configurations for all five difficulty profiles.
# Note: Elo ratings are explicitly avoided per design directives;
# difficulty describes relative playing strength and computational depth.
DIFFICULTY_PROFILES: Dict[DifficultyLevel, DifficultyProfile] = {
    DifficultyLevel.BEGINNER: DifficultyProfile(
        level=DifficultyLevel.BEGINNER,
        display_name="Beginner",
        description="Fast 1-ply tactical vision with minimal node budget and safe check evasion.",
        search_config=SearchConfig(
            depth=1,
            algorithm="alpha_beta",
            time_limit_ms=250.0,
            max_nodes=300,
            use_iterative_deepening=False,
            use_move_ordering=False,
            use_quiescence=True,
            max_quiescence_depth=0,
            max_check_depth=1,
            use_transposition_table=False,
            transposition_table_size_mb=4,
        ),
        base_time_ms=100.0,
        max_time_ms=250.0,
        min_time_ms=25.0,
    ),
    DifficultyLevel.EASY: DifficultyProfile(
        level=DifficultyLevel.EASY,
        display_name="Easy",
        description="2-ply search with shallow quiescence extensions and move ordering.",
        search_config=SearchConfig(
            depth=2,
            algorithm="iterative_deepening",
            time_limit_ms=600.0,
            max_nodes=3_000,
            use_iterative_deepening=True,
            use_move_ordering=True,
            use_quiescence=True,
            max_quiescence_depth=2,
            max_check_depth=1,
            use_transposition_table=True,
            transposition_table_size_mb=8,
        ),
        base_time_ms=300.0,
        max_time_ms=600.0,
        min_time_ms=50.0,
    ),
    DifficultyLevel.MEDIUM: DifficultyProfile(
        level=DifficultyLevel.MEDIUM,
        display_name="Medium",
        description="Balanced 3-ply iterative deepening with 4-ply quiescence and TT caching.",
        search_config=SearchConfig(
            depth=3,
            algorithm="iterative_deepening",
            time_limit_ms=1_500.0,
            max_nodes=20_000,
            use_iterative_deepening=True,
            use_move_ordering=True,
            use_quiescence=True,
            max_quiescence_depth=4,
            max_check_depth=2,
            use_transposition_table=True,
            transposition_table_size_mb=16,
        ),
        base_time_ms=800.0,
        max_time_ms=1_500.0,
        min_time_ms=100.0,
    ),
    DifficultyLevel.HARD: DifficultyProfile(
        level=DifficultyLevel.HARD,
        display_name="Hard",
        description="Deep 4-ply search with 6-ply quiescence extensions and full move ordering.",
        search_config=SearchConfig(
            depth=4,
            algorithm="iterative_deepening",
            time_limit_ms=3_500.0,
            max_nodes=80_000,
            use_iterative_deepening=True,
            use_move_ordering=True,
            use_quiescence=True,
            max_quiescence_depth=6,
            max_check_depth=2,
            use_transposition_table=True,
            transposition_table_size_mb=32,
        ),
        base_time_ms=2_000.0,
        max_time_ms=3_500.0,
        min_time_ms=200.0,
    ),
    DifficultyLevel.EXPERT: DifficultyProfile(
        level=DifficultyLevel.EXPERT,
        display_name="Expert",
        description="Full 5-ply search with deep 8-ply quiescence and 64MB transposition table.",
        search_config=SearchConfig(
            depth=5,
            algorithm="iterative_deepening",
            time_limit_ms=6_000.0,
            max_nodes=250_000,
            use_iterative_deepening=True,
            use_move_ordering=True,
            use_quiescence=True,
            max_quiescence_depth=8,
            max_check_depth=2,
            use_transposition_table=True,
            transposition_table_size_mb=64,
        ),
        base_time_ms=4_000.0,
        max_time_ms=6_000.0,
        min_time_ms=300.0,
    ),
}

DEFAULT_DIFFICULTY = DifficultyLevel.MEDIUM


def get_difficulty_profile(level: Union[str, DifficultyLevel] = DEFAULT_DIFFICULTY) -> DifficultyProfile:
    """
    Retrieves the immutable DifficultyProfile for the specified difficulty level.
    
    Args:
        level: Case-insensitive difficulty string or DifficultyLevel enum.
        
    Returns:
        The matching DifficultyProfile.
        
    Raises:
        ValueError: If the requested difficulty name is unrecognized.
    """
    if isinstance(level, DifficultyLevel):
        return DIFFICULTY_PROFILES[level]

    if not isinstance(level, str):
        raise ValueError(
            f"Difficulty must be a string or DifficultyLevel, got {type(level).__name__}"
        )

    cleaned = level.strip().lower()
    try:
        enum_val = DifficultyLevel(cleaned)
        return DIFFICULTY_PROFILES[enum_val]
    except ValueError:
        valid_options = ", ".join(d.value for d in DifficultyLevel)
        raise ValueError(
            f"Invalid difficulty '{level}'. Supported difficulties are: {valid_options}"
        )


def validate_difficulty(level: str) -> str:
    """
    Validates a difficulty string and returns its normalized canonical name.
    
    Args:
        level: Case-insensitive difficulty string.
        
    Returns:
        Canonical lowercase difficulty string (e.g. 'medium').
        
    Raises:
        ValueError: If the difficulty string is invalid.
    """
    profile = get_difficulty_profile(level)
    return profile.level.value
