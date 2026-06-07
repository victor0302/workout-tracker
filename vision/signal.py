"""Signal-extraction and filtering for the rep counter.

Dep-free on purpose (math + the Keypoint shape only): tests, replay
and synthesis tooling all import from here without pulling cv2,
mediapipe or numpy.

Smoothers (EMASmoother, MedianSmoother) follow the skip-on-None
contract: update(None) returns None and does not mutate internal
state, so a missing-pose frame doesn't fabricate signal or reset
filter history.
"""

import math
import statistics
from collections import deque
from typing import Protocol

from .recording import Keypoint

_LEG_JOINTS = ("HIP", "KNEE", "ANKLE")


def joint_angle(a: Keypoint, b: Keypoint, c: Keypoint) -> float:
    """Angle at vertex b formed by a-b-c, in degrees."""
    bax, bay = a.x - b.x, a.y - b.y
    bcx, bcy = c.x - b.x, c.y - b.y
    dot = bax * bcx + bay * bcy
    mag = math.sqrt(bax * bax + bay * bay) * math.sqrt(bcx * bcx + bcy * bcy)
    if mag == 0.0:
        return 0.0
    cos = max(-1.0, min(1.0, dot / mag))
    return math.degrees(math.acos(cos))


def knee_angle(
    keypoints: dict[str, Keypoint],
    vis_threshold: float = 0.5,
) -> float | None:
    """Mean of left and right knee angles, falling back to the visible leg.

    Returns None if neither leg has all three of HIP/KNEE/ANKLE present
    with visibility >= vis_threshold — the rep counter skips that frame.
    """
    left = _leg_angle(keypoints, "LEFT", vis_threshold)
    right = _leg_angle(keypoints, "RIGHT", vis_threshold)
    if left is not None and right is not None:
        return (left + right) / 2
    return left if left is not None else right


def _leg_angle(
    keypoints: dict[str, Keypoint],
    side: str,
    vis_threshold: float,
) -> float | None:
    landmarks = [keypoints.get(f"{side}_{joint}") for joint in _LEG_JOINTS]
    if not all(landmarks):
        return None
    if min(lm.visibility for lm in landmarks) < vis_threshold:
        return None
    hip, knee, ankle = landmarks
    return joint_angle(hip, knee, ankle)


class Smoother(Protocol):
    """Stateful 1D filter. update(None) returns None and preserves state."""

    def update(self, x: float | None) -> float | None: ...
    def reset(self) -> None: ...


class EMASmoother:
    """Exponential moving average: out = alpha * x + (1 - alpha) * prev.

    Small alpha = heavier smoothing + more lag. Default 0.3 trades
    ~3 frames of lag at 30 fps against meaningful jitter rejection.
    """

    def __init__(self, alpha: float = 0.3):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._value: float | None = None

    def update(self, x: float | None) -> float | None:
        if x is None:
            return None
        if self._value is None:
            self._value = x
        else:
            self._value = self.alpha * x + (1.0 - self.alpha) * self._value
        return self._value

    def reset(self) -> None:
        self._value = None


class MedianSmoother:
    """Sliding-window median. Robust to single-frame outliers; almost no lag."""

    def __init__(self, window: int = 5):
        if window < 1:
            raise ValueError("window must be >= 1")
        self.window = window
        self._buffer: deque[float] = deque(maxlen=window)

    def update(self, x: float | None) -> float | None:
        if x is None:
            return None
        self._buffer.append(x)
        return statistics.median(self._buffer)

    def reset(self) -> None:
        self._buffer.clear()
