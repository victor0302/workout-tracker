"""State machine that counts reps from a 1D signal (e.g. knee angle).

The counter watches the signal cross a `down` threshold, stay past it
long enough to be a real movement (hysteresis), and then come back
across the `up` threshold the same way to log one rep.

`dwell_frames` is the minimum number of consecutive frames the signal
must spend past a threshold before the counter commits the
transition. Set it to 1 to disable hysteresis and get the original
single-sample behavior; default 5 (≈150ms at 30fps) rejects jitter
that briefly crosses a threshold and then crosses back.
"""

from dataclasses import dataclass


@dataclass
class RepCounter:
    down_threshold: float
    up_threshold: float
    dwell_frames: int = 5
    count: int = 0
    _state: str = "up"  # committed state: "up" or "down"
    _pending_frames: int = 0  # consecutive frames supporting a transition

    def __post_init__(self) -> None:
        if self.dwell_frames < 1:
            raise ValueError("dwell_frames must be >= 1")

    def update(self, signal: float) -> int:
        if self._state == "up":
            if signal < self.down_threshold:
                self._pending_frames += 1
                if self._pending_frames >= self.dwell_frames:
                    self._state = "down"
                    self._pending_frames = 0
            else:
                self._pending_frames = 0
        else:  # _state == "down"
            if signal > self.up_threshold:
                self._pending_frames += 1
                if self._pending_frames >= self.dwell_frames:
                    self._state = "up"
                    self._pending_frames = 0
                    self.count += 1
            else:
                self._pending_frames = 0
        return self.count

    def reset(self) -> None:
        self.count = 0
        self._state = "up"
        self._pending_frames = 0
