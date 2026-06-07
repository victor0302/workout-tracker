"""Signal-extraction helpers for the rep counter.

Dep-free on purpose (math + the Keypoint shape only): tests, replay
and synthesis tooling all import from here without pulling cv2,
mediapipe or numpy.
"""

import math

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
