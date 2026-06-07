"""Signal module tests — joint_angle, knee_angle, smoothers."""

import math
import random

import pytest

from vision.recording import Keypoint
from vision.signal import EMASmoother, MedianSmoother, joint_angle, knee_angle


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


class TestEMASmoother:
    def test_first_sample_seeds_state(self):
        s = EMASmoother(alpha=0.3)
        assert s.update(100.0) == 100.0

    def test_converges_to_constant_input(self):
        s = EMASmoother(alpha=0.3)
        s.update(100.0)
        for _ in range(50):
            s.update(50.0)
        assert s.update(50.0) == pytest.approx(50.0, abs=1e-3)

    def test_alpha_one_is_passthrough(self):
        s = EMASmoother(alpha=1.0)
        for x in [10.0, 200.0, -5.0]:
            assert s.update(x) == x

    def test_alpha_must_be_in_open_unit_interval(self):
        with pytest.raises(ValueError):
            EMASmoother(alpha=0.0)
        with pytest.raises(ValueError):
            EMASmoother(alpha=1.5)

    def test_none_returns_none_and_preserves_state(self):
        s = EMASmoother(alpha=0.3)
        s.update(100.0)
        assert s.update(None) is None
        # State preserved — next real sample blends with 100, not seeded fresh.
        assert s.update(100.0) == pytest.approx(100.0)

    def test_reset_clears_state(self):
        s = EMASmoother(alpha=0.3)
        s.update(100.0)
        s.reset()
        # Next sample seeds fresh, not blended against the old 100.
        assert s.update(50.0) == 50.0

    def test_reduces_variance_on_noisy_constant(self):
        rng = random.Random(1)
        noisy = [100.0 + rng.uniform(-10, 10) for _ in range(200)]
        s = EMASmoother(alpha=0.3)
        smoothed = [s.update(x) for x in noisy]
        # Use the tail to skip the warm-up phase.
        raw_var = _variance(noisy[100:])
        smoothed_var = _variance(smoothed[100:])
        assert smoothed_var < raw_var / 3


class TestMedianSmoother:
    def test_window_size_one_is_passthrough(self):
        s = MedianSmoother(window=1)
        for x in [10.0, 200.0, -5.0]:
            assert s.update(x) == x

    def test_returns_median_of_filled_window(self):
        s = MedianSmoother(window=5)
        for x in [1.0, 2.0, 3.0, 4.0, 5.0]:
            s.update(x)
        # window now [1, 2, 3, 4, 5], median = 3
        assert s.update(6.0) == 4.0  # window [2, 3, 4, 5, 6]

    def test_partial_window_returns_running_median(self):
        s = MedianSmoother(window=5)
        assert s.update(10.0) == 10.0
        assert s.update(20.0) == 15.0  # median of [10, 20]
        assert s.update(30.0) == 20.0  # median of [10, 20, 30]

    def test_window_must_be_positive(self):
        with pytest.raises(ValueError):
            MedianSmoother(window=0)

    def test_robust_to_single_outlier(self):
        s = MedianSmoother(window=5)
        for x in [100.0, 100.0, 100.0, 100.0]:
            s.update(x)
        # One huge outlier should not move the median much.
        assert s.update(10000.0) == 100.0

    def test_none_returns_none_and_preserves_state(self):
        s = MedianSmoother(window=3)
        s.update(10.0)
        s.update(20.0)
        assert s.update(None) is None
        # Buffer still [10, 20] — next real sample joins the existing window.
        assert s.update(30.0) == 20.0

    def test_reset_clears_state(self):
        s = MedianSmoother(window=3)
        s.update(10.0)
        s.update(20.0)
        s.reset()
        assert s.update(5.0) == 5.0


def _variance(xs: list[float]) -> float:
    n = len(xs)
    mean = sum(xs) / n
    return sum((x - mean) ** 2 for x in xs) / n
