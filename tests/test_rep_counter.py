"""Phase 1 (5/9): RepCounter hysteresis.

The state machine should only commit a transition after the signal has
spent `dwell_frames` consecutive samples past the relevant threshold.
A single-frame excursion across the threshold should not produce a
state transition or a counted rep.
"""

import pytest

from vision.rep_counter import RepCounter


def _feed(counter: RepCounter, signal: list[float]) -> int:
    for x in signal:
        counter.update(x)
    return counter.count


class TestNoHysteresis:
    def test_dwell_one_matches_naive_behavior(self):
        c = RepCounter(down_threshold=90.0, up_threshold=160.0, dwell_frames=1)
        # Single down sample then single up sample = one rep.
        c.update(170.0)
        c.update(80.0)
        c.update(170.0)
        assert c.count == 1


class TestHysteresis:
    def test_full_cycle_counts_one_rep(self):
        c = RepCounter(down_threshold=90.0, up_threshold=160.0, dwell_frames=5)
        signal = [170.0] + [80.0] * 5 + [170.0] * 5
        assert _feed(c, signal) == 1

    def test_below_threshold_for_fewer_than_dwell_frames_does_not_transition(self):
        c = RepCounter(down_threshold=90.0, up_threshold=160.0, dwell_frames=5)
        # 4 frames below — one short of dwell.
        signal = [170.0] + [80.0] * 4 + [170.0] * 10
        assert _feed(c, signal) == 0
        assert c._state == "up"

    def test_cross_back_resets_pending(self):
        c = RepCounter(down_threshold=90.0, up_threshold=160.0, dwell_frames=5)
        # 3 frames below, then crosses back, then 5 frames below.
        # Should commit down after the second run of 5 — pending reset on crossback.
        signal = [80.0] * 3 + [170.0] + [80.0] * 5
        _feed(c, signal)
        assert c._state == "down"
        # No up transition yet, count still 0.
        assert c.count == 0

    def test_single_outlier_does_not_transition(self):
        c = RepCounter(down_threshold=90.0, up_threshold=160.0, dwell_frames=5)
        # One spike below 90 surrounded by signal above 90 = noise, not a rep.
        signal = [170.0, 170.0, 80.0, 170.0, 170.0, 170.0]
        assert _feed(c, signal) == 0
        assert c._state == "up"

    def test_up_transition_requires_dwell_frames_above(self):
        c = RepCounter(down_threshold=90.0, up_threshold=160.0, dwell_frames=5)
        # Drive into down state first.
        _feed(c, [80.0] * 5)
        assert c._state == "down"
        # 4 frames above 160 — one short — should not count yet.
        _feed(c, [170.0] * 4)
        assert c.count == 0
        # 5th frame commits.
        c.update(170.0)
        assert c.count == 1
        assert c._state == "up"

    def test_signal_in_indeterminate_zone_resets_pending(self):
        c = RepCounter(down_threshold=90.0, up_threshold=160.0, dwell_frames=5)
        # While in "up" state, the indeterminate zone (between 90 and 160)
        # counts as "not below 90" → pending resets.
        signal = [80.0] * 3 + [120.0] + [80.0] * 4
        _feed(c, signal)
        # Only the last 4 below-90 frames count, less than dwell, no transition.
        assert c._state == "up"

    def test_dwell_frames_must_be_positive(self):
        with pytest.raises(ValueError):
            RepCounter(down_threshold=90.0, up_threshold=160.0, dwell_frames=0)
        with pytest.raises(ValueError):
            RepCounter(down_threshold=90.0, up_threshold=160.0, dwell_frames=-3)


class TestReset:
    def test_reset_clears_state_count_and_pending(self):
        c = RepCounter(down_threshold=90.0, up_threshold=160.0, dwell_frames=5)
        _feed(c, [80.0] * 5 + [170.0] * 5)  # one full cycle
        assert c.count == 1
        # Build up some pending without committing.
        _feed(c, [80.0] * 3)
        c.reset()
        assert c.count == 0
        assert c._state == "up"
        assert c._pending_frames == 0


class TestDefaults:
    def test_default_dwell_frames(self):
        c = RepCounter(down_threshold=90.0, up_threshold=160.0)
        assert c.dwell_frames == 5
