"""Exercise classifier stub.

Real version would take a window of keypoints and run a small temporal
model (LSTM / 1D CNN / GRU). For now it returns "unknown" and exposes
the labels the rest of the system expects.
"""

from collections import deque
from typing import Literal

from .pose_estimator import Keypoint

Exercise = Literal["squat", "curl", "deadlift", "unknown"]
LABELS: tuple[Exercise, ...] = ("squat", "curl", "deadlift", "unknown")


class ExerciseClassifier:
    def __init__(self, window: int = 30):
        self._buffer: deque[dict[str, Keypoint]] = deque(maxlen=window)

    def update(self, keypoints: dict[str, Keypoint]) -> Exercise:
        self._buffer.append(keypoints)
        if len(self._buffer) < self._buffer.maxlen:
            return "unknown"
        # TODO: replace with a trained temporal model over self._buffer.
        return "unknown"
