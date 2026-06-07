"""Phase 1 (3/9): joint_angle + knee_angle (averaged with visibility fallback)."""

import math

import pytest

from vision.recording import Keypoint
from vision.signal import joint_angle, knee_angle


def _kp(x: float, y: float, vis: float = 1.0) -> Keypoint:
    return Keypoint(x=x, y=y, z=0.0, visibility=vis)


def _leg(angle_deg: float, vis: float = 1.0, side: str = "RIGHT") -> dict[str, Keypoint]:
    """Three keypoints that produce `angle_deg` at the knee vertex."""
    rad = math.radians(angle_deg)
    return {
        f"{side}_HIP": _kp(0.0, 1.0, vis),
        f"{side}_KNEE": _kp(0.0, 0.0, vis),
        f"{side}_ANKLE": _kp(math.sin(rad), math.cos(rad), vis),
    }


class TestJointAngle:
    def test_straight(self):
        a, b, c = _kp(0, 1), _kp(0, 0), _kp(0, -1)
        assert joint_angle(a, b, c) == pytest.approx(180.0)

    def test_right_angle(self):
        a, b, c = _kp(0, 1), _kp(0, 0), _kp(1, 0)
        assert joint_angle(a, b, c) == pytest.approx(90.0)

    def test_zero_when_vectors_collapse(self):
        # Degenerate: b coincides with a. Don't divide-by-zero; return 0.
        a = b = _kp(0, 0)
        c = _kp(1, 0)
        assert joint_angle(a, b, c) == 0.0

    @pytest.mark.parametrize("target", [30.0, 45.0, 90.0, 135.0, 170.0])
    def test_roundtrip_through_leg_constructor(self, target):
        leg = _leg(target)
        hip, knee, ankle = leg["RIGHT_HIP"], leg["RIGHT_KNEE"], leg["RIGHT_ANKLE"]
        assert joint_angle(hip, knee, ankle) == pytest.approx(target, abs=1e-6)


class TestKneeAngle:
    def test_both_legs_visible_returns_mean(self):
        kp = {**_leg(120.0, side="LEFT"), **_leg(160.0, side="RIGHT")}
        assert knee_angle(kp) == pytest.approx(140.0)

    def test_only_right_visible_falls_back_to_right(self):
        kp = _leg(150.0, side="RIGHT")
        assert knee_angle(kp) == pytest.approx(150.0)

    def test_only_left_visible_falls_back_to_left(self):
        kp = _leg(100.0, side="LEFT")
        assert knee_angle(kp) == pytest.approx(100.0)

    def test_no_legs_visible_returns_none(self):
        assert knee_angle({}) is None

    def test_low_visibility_leg_is_ignored(self):
        # Left is fully visible at 100°; right has one low-vis landmark and is dropped.
        kp = {**_leg(100.0, vis=1.0, side="LEFT"), **_leg(140.0, side="RIGHT")}
        kp["RIGHT_ANKLE"] = _kp(kp["RIGHT_ANKLE"].x, kp["RIGHT_ANKLE"].y, vis=0.1)
        assert knee_angle(kp) == pytest.approx(100.0)

    def test_both_legs_low_visibility_returns_none(self):
        kp = {**_leg(100.0, vis=0.2, side="LEFT"), **_leg(140.0, vis=0.1, side="RIGHT")}
        assert knee_angle(kp) is None

    def test_partial_landmarks_one_side_treated_as_missing(self):
        # Right has hip + knee but no ankle → right is incomplete, fall back to left.
        kp = _leg(100.0, side="LEFT")
        kp["RIGHT_HIP"] = _kp(0.0, 1.0)
        kp["RIGHT_KNEE"] = _kp(0.0, 0.0)
        assert knee_angle(kp) == pytest.approx(100.0)

    def test_visibility_threshold_is_configurable(self):
        kp = _leg(100.0, vis=0.4, side="LEFT")
        assert knee_angle(kp, vis_threshold=0.5) is None
        assert knee_angle(kp, vis_threshold=0.3) == pytest.approx(100.0)
