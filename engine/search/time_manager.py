"""Dynamic Time Management Layer for Chess AI Adversarial Search.

Allocates move budgets based on legal move count, game phase, tactical pressure
(e.g., checks), and principal variation stability, while enforcing strict safety margins
over a monotonic clock.
"""

import time
from typing import Optional
import chess

from engine.difficulty import DifficultyProfile
from engine.evaluation.game_phase import calculate_game_phase


# Safety margin in milliseconds reserved for stack unwinding,
# move formatting, and API serialization overhead.
DEFAULT_SAFETY_MARGIN_MS: float = 50.0


class TimeManager:
    """
    Computes per-move search time allocations and manages early termination criteria.
    
    Guarantees:
    - Never allocates less than profile.min_time_ms or more than profile.max_time_ms.
    - Always reserves safety margin for external caller overhead.
    - Monotonic clock measurements via time.perf_counter().
    - Never confuses per-move budgets with whole-game clocks.
    """

    def __init__(self, safety_margin_ms: float = DEFAULT_SAFETY_MARGIN_MS) -> None:
        """
        Initialize TimeManager.
        
        Args:
            safety_margin_ms: Milliseconds deducted from allocated budget for Python overhead.
        """
        if safety_margin_ms < 0:
            raise ValueError(f"safety_margin_ms must be non-negative, got {safety_margin_ms}")
        self.safety_margin_ms = safety_margin_ms

    def allocate_time(
        self,
        board: chess.Board,
        profile: DifficultyProfile,
    ) -> float:
        """
        Calculates the allocated time budget in milliseconds for a move in the given position.
        
        Factors considered:
        1. Single Legal Move: If only 1 legal move exists, no decision is required;
           returns min_time_ms immediately.
        2. Legal Move Count (Branching Factor):
           Positions with fewer moves (< 10) have smaller branching trees and require less time.
           Positions with many moves (> 35) require broader exploration.
        3. Game Phase (Opening / Middlegame / Endgame):
           Calculated via tapered piece values. Middlegames with high piece complexity
           receive the highest allocation (+15%), while simplified endgames receive
           a reduced allocation (-15%).
        4. Tactical Pressure / King in Check:
           If the side to move is currently in check, evasion lines must be verified
           carefully (+30% boost).
        
        Args:
            board: Authoritative python-chess Board.
            profile: Selected DifficultyProfile defining base, min, and max budgets.
            
        Returns:
            Allocated time in milliseconds, strictly bounded within [min_time_ms, max_time_ms].
        """
        legal_move_count = board.legal_moves.count()

        # Factor 1: Single legal move requires no search effort
        if legal_move_count <= 1:
            return float(profile.min_time_ms)

        base_ms = profile.base_time_ms

        # Factor 2: Branching factor / legal move count scaling
        # Typical chess positions have ~30-35 legal moves.
        # Scale between 0.75 (few moves) and 1.15 (many moves).
        # When in check, legal moves are naturally restricted by check arbitration,
        # so we do not suppress calculation time with a low move-count factor.
        if board.is_check():
            move_factor = 1.00
        elif legal_move_count < 10:
            move_factor = 0.75
        elif legal_move_count < 20:
            move_factor = 0.90
        elif legal_move_count <= 40:
            move_factor = 1.00
        else:
            move_factor = 1.15

        # Factor 3: Game phase scaling
        # Phase 1.0 = opening, 0.5 = middlegame, 0.0 = endgame
        try:
            phase = calculate_game_phase(board)
        except Exception:
            phase = 0.5

        if 0.25 <= phase <= 0.80:
            # Peak middlegame complexity
            phase_factor = 1.15
        elif phase > 0.80:
            # Opening development: standard lines
            phase_factor = 0.95
        else:
            # Endgame: fewer pieces, narrower branches
            phase_factor = 0.85

        # Factor 4: Tactical urgency (king in check)
        check_factor = 1.30 if board.is_check() else 1.00

        # Calculate raw allocated budget
        allocated_ms = base_ms * move_factor * phase_factor * check_factor

        # Strictly clamp within profile bounds
        bounded_ms = max(profile.min_time_ms, min(profile.max_time_ms, allocated_ms))
        return round(bounded_ms, 2)

    def get_effective_search_limit(
        self,
        allocated_time_ms: float,
        min_time_ms: float,
    ) -> float:
        """
        Computes the effective search limit given an allocated budget and safety margin.
        
        Args:
            allocated_time_ms: Total time allocated for this move.
            min_time_ms: Minimum threshold allowed for search.
            
        Returns:
            Effective search limit ms passed to SearchContext.
        """
        return max(min_time_ms, allocated_time_ms - self.safety_margin_ms)

    def should_terminate_early(
        self,
        elapsed_ms: float,
        allocated_ms: float,
        completed_depth: int,
        pv_stable_iterations: int = 1,
        score_diff_cp: Optional[int] = None,
    ) -> bool:
        """
        Determines whether iterative deepening should stop before starting the next depth.
        
        Since chess search trees grow at a branching factor of b ~ 3 to 5,
        the next iteration will take roughly 3x-5x longer than the current iteration.
        If we have already consumed over 50-60% of our allocated budget, launching
        the next depth is almost guaranteed to be aborted mid-search, wasting CPU.
        
        Furthermore, if the best move has remained completely stable across 2+ iterations
        and the score evaluation is steady, further search has diminishing returns.
        
        Args:
            elapsed_ms: Time consumed so far in milliseconds.
            allocated_ms: Total allocated budget for this move.
            completed_depth: Deepest iteration completed so far.
            pv_stable_iterations: Number of consecutive iterations where best move didn't change.
            score_diff_cp: Absolute score difference between last two iterations (if available).
            
        Returns:
            True if search should conclude cleanly with the last completed iteration.
        """
        if completed_depth < 2:
            # Always complete at least depth 1 (and preferably depth 2 if budget allows)
            return False

        # If we have used >= 60% of our allocated budget, the next iteration will exceed it
        time_ratio = elapsed_ms / allocated_ms if allocated_ms > 0 else 1.0
        if time_ratio >= 0.60:
            return True

        # If PV move has been stable for 2+ depths and score hasn't swung violently
        if completed_depth >= 3 and pv_stable_iterations >= 2:
            if score_diff_cp is not None and score_diff_cp <= 25 and time_ratio >= 0.40:
                return True

        return False
