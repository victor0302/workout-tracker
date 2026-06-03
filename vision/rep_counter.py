"""Generic rep counter driven by a single 1D signal (e.g. joint angle).

The counter is a small state machine: it watches the signal cross a
"down" threshold and then come back across an "up" threshold to log
one rep. Thresholds are exercise-specific and supplied by the caller.
"""

from dataclasses import dataclass


@dataclass
class RepCounter:
    down_threshold: float
    up_threshold: float
    count: int = 0
    _state: str = "up"  # "up" or "down"

    def update(self, signal: float) -> int:
        if self._state == "up" and signal < self.down_threshold:
            self._state = "down"
        elif self._state == "down" and signal > self.up_threshold:
            self._state = "up"
            self.count += 1
        return self.count

    def reset(self) -> None:
        self.count = 0
        self._state = "up"
