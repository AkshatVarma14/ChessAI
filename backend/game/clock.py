"""Authoritative Chess Clock implementation supporting five FIDE/standard time control presets."""

from dataclasses import dataclass
import time
from typing import Callable, Dict, Literal, Optional, Tuple

from backend.game.models import Color

TimeControlType = Literal["bullet", "blitz", "rapid", "classic", "casual"]

VALID_TIME_CONTROLS: Tuple[TimeControlType, ...] = (
    "bullet",
    "blitz",
    "rapid",
    "classic",
    "casual",
)

TIME_CONTROL_DURATIONS: Dict[str, Optional[float]] = {
    "bullet": 60.0,    # 1 minute, 0s increment
    "blitz": 180.0,    # 3 minutes, 0s increment
    "rapid": 600.0,    # 10 minutes, 0s increment (default)
    "classic": 1800.0, # 30 minutes, 0s increment
    "casual": None,    # Unlimited, untimed
}

DEFAULT_TIME_CONTROL: TimeControlType = "rapid"


def validate_time_control(time_control: str) -> TimeControlType:
    """
    Validates and normalizes a time control preset string.
    
    Args:
        time_control: Case-insensitive time control mode string.
        
    Returns:
        Normalized TimeControlType ('bullet', 'blitz', 'rapid', 'classic', 'casual').
        
    Raises:
        ValueError: If the time control is unsupported or malformed.
    """
    if not isinstance(time_control, str):
        raise ValueError(f"Time control must be a string, got {type(time_control).__name__}")

    normalized = time_control.strip().lower()
    if normalized not in TIME_CONTROL_DURATIONS:
        valid_options = ", ".join(repr(k) for k in VALID_TIME_CONTROLS)
        raise ValueError(
            f"Invalid time control '{time_control}'. Must be one of: {valid_options}"
        )
    return normalized  # type: ignore[return-value]


@dataclass(frozen=True)
class ClockSnapshot:
    """Immutable snapshot of chess clock state for lossless undo restoration."""

    white_time: Optional[float]
    black_time: Optional[float]
    clock_started: bool
    timed_out_color: Optional[Color]


class ChessClock:
    """
    Authoritative stateful representation of chess clocks for both players.
    
    Uses monotonic time source for precise elapsed-time tracking without
    wall-clock jitter. Manages move-by-move clock switching, timeout detection,
    and lossless state snapshots for single-ply undo.
    """

    def __init__(
        self,
        time_control: str = DEFAULT_TIME_CONTROL,
        time_source: Optional[Callable[[], float]] = None,
    ) -> None:
        self._time_control: TimeControlType = validate_time_control(time_control)
        self._is_timed: bool = (self._time_control != "casual")
        self._time_source: Callable[[], float] = time_source or time.perf_counter

        init_duration = TIME_CONTROL_DURATIONS[self._time_control]
        self._white_time: Optional[float] = init_duration
        self._black_time: Optional[float] = init_duration
        self._clock_started: bool = False
        self._last_update: Optional[float] = None
        self._timed_out_color: Optional[Color] = None
        self._history: list[ClockSnapshot] = [self.snapshot()]

    @property
    def time_control(self) -> TimeControlType:
        """Active time control preset."""
        return self._time_control

    @property
    def is_timed(self) -> bool:
        """True if the game uses countdown clocks (False for Casual)."""
        return self._is_timed

    @property
    def clock_started(self) -> bool:
        """True if the clock has started running (activated on first legal move)."""
        return self._clock_started

    @property
    def timed_out_color(self) -> Optional[Color]:
        """Color of the player whose clock reached 0.0, or None if no timeout."""
        return self._timed_out_color

    @property
    def white_time(self) -> Optional[float]:
        """Remaining time for White in seconds (None if Casual)."""
        return self._white_time

    @property
    def black_time(self) -> Optional[float]:
        """Remaining time for Black in seconds (None if Casual)."""
        return self._black_time

    def snapshot(self) -> ClockSnapshot:
        """Produces an immutable snapshot of current clock state."""
        return ClockSnapshot(
            white_time=self._white_time,
            black_time=self._black_time,
            clock_started=self._clock_started,
            timed_out_color=self._timed_out_color,
        )

    def record_snapshot(self) -> None:
        """Appends current snapshot to history (invoked after each legal move)."""
        self._history.append(self.snapshot())

    def update(self, active_turn: Color) -> Optional[Color]:
        """
        Deducts elapsed monotonic time from the active side's clock.
        
        Args:
            active_turn: Side currently on move ('white' or 'black').
            
        Returns:
            Color of player who timed out, or None if both clocks have time remaining.
        """
        if not self._is_timed or not self._clock_started or self._timed_out_color is not None:
            return self._timed_out_color

        now = self._time_source()
        if self._last_update is None:
            self._last_update = now
            return None

        elapsed = now - self._last_update
        self._last_update = now

        if active_turn == "white":
            if self._white_time is not None:
                self._white_time = max(0.0, self._white_time - elapsed)
                if self._white_time <= 0.0:
                    self._timed_out_color = "white"
        else:
            if self._black_time is not None:
                self._black_time = max(0.0, self._black_time - elapsed)
                if self._black_time <= 0.0:
                    self._timed_out_color = "black"

        return self._timed_out_color

    def on_move_executed(self) -> None:
        """
        Switches the active clock after a legal move is pushed.
        
        Activates clock on the first legal move, and resets the elapsed time anchor.
        """
        if not self._is_timed:
            return

        now = self._time_source()
        if not self._clock_started:
            # First legal move in the game starts the clock!
            self._clock_started = True

        self._last_update = now

    def deduct_time(self, color: Color, elapsed_seconds: float) -> Optional[Color]:
        """
        Deducts specific elapsed time from a player's clock (e.g. AI thinking time).
        
        Args:
            color: Side whose clock is being deducted.
            elapsed_seconds: Elapsed duration in seconds.
            
        Returns:
            Color of player who timed out, or None.
        """
        if not self._is_timed or self._timed_out_color is not None or elapsed_seconds <= 0.0:
            return self._timed_out_color

        if color == "white":
            if self._white_time is not None:
                self._white_time = max(0.0, self._white_time - elapsed_seconds)
                if self._white_time <= 0.0:
                    self._timed_out_color = "white"
        else:
            if self._black_time is not None:
                self._black_time = max(0.0, self._black_time - elapsed_seconds)
                if self._black_time <= 0.0:
                    self._timed_out_color = "black"

        self._last_update = self._time_source()
        return self._timed_out_color

    def undo(self, plies: int) -> None:
        """
        Restores clock state to the snapshot plies moves ago.
        
        Args:
            plies: Number of plies being undone.
        """
        if not self._is_timed:
            return

        for _ in range(plies):
            if len(self._history) > 1:
                self._history.pop()

        snap = self._history[-1]
        self._white_time = snap.white_time
        self._black_time = snap.black_time
        self._clock_started = snap.clock_started
        self._timed_out_color = snap.timed_out_color
        self._last_update = self._time_source() if self._clock_started else None

    def reset(self) -> None:
        """Resets both clocks to starting time controls."""
        init_duration = TIME_CONTROL_DURATIONS[self._time_control]
        self._white_time = init_duration
        self._black_time = init_duration
        self._clock_started = False
        self._last_update = None
        self._timed_out_color = None
        self._history = [self.snapshot()]
