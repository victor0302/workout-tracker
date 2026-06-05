"""Phase 1 (1/9): record/replay round-trip + synthetic-rep counting."""

import json
import math
from pathlib import Path

from vision.main import build_record
from vision.pose_estimator import Keypoint
from vision.replay import iter_jsonl, replay


def _synthetic_keypoints(angle_deg: float) -> dict[str, Keypoint]:
    """Three keypoints constructed so joint_angle(hip, knee, ankle) == angle_deg.

    knee at origin, hip straight up, ankle rotated `angle_deg` from the
    hip vector. Coordinates are normalized [0, 1]-ish but the rep
    counter only cares about the resulting angle.
    """
    rad = math.radians(angle_deg)
    return {
        "RIGHT_HIP": Keypoint(x=0.0, y=1.0, z=0.0, visibility=1.0),
        "RIGHT_KNEE": Keypoint(x=0.0, y=0.0, z=0.0, visibility=1.0),
        "RIGHT_ANKLE": Keypoint(x=math.sin(rad), y=math.cos(rad), z=0.0, visibility=1.0),
    }


def _write_clip(path: Path, records: list[dict]) -> None:
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _angle_sweep(n_reps: int, fps: int = 30, samples_per_rep: int = 60) -> list[dict]:
    """One JSONL record per frame across n_reps clean squats (170° → 70° → 170°)."""
    records: list[dict] = []
    for rep in range(n_reps):
        for i in range(samples_per_rep):
            phase = i / samples_per_rep
            angle_deg = 120.0 + 50.0 * math.cos(2 * math.pi * phase)
            ts = (rep * samples_per_rep + i) / fps
            records.append(build_record(ts, _synthetic_keypoints(angle_deg)))
    return records


def test_build_record_round_trip_through_iter_jsonl(tmp_path: Path):
    clip = tmp_path / "clip.jsonl"
    src = [build_record(t / 30, _synthetic_keypoints(170.0)) for t in range(5)]
    _write_clip(clip, src)

    loaded = list(iter_jsonl(clip))
    assert loaded == src


def test_build_record_handles_missing_pose():
    record = build_record(ts=1.0, keypoints=None)
    assert record == {"ts": 1.0, "keypoints": None}


def test_replay_counts_synthetic_clean_reps(tmp_path: Path):
    clip = tmp_path / "five.jsonl"
    _write_clip(clip, _angle_sweep(n_reps=5))
    assert replay(clip) == 5


def test_replay_zero_for_standing_still(tmp_path: Path):
    clip = tmp_path / "still.jsonl"
    records = [build_record(t / 30, _synthetic_keypoints(175.0)) for t in range(150)]
    _write_clip(clip, records)
    assert replay(clip) == 0


def test_replay_skips_null_keypoint_frames(tmp_path: Path):
    clip = tmp_path / "nulls.jsonl"
    records = [
        build_record(0.0, _synthetic_keypoints(170.0)),
        build_record(0.033, None),
        build_record(0.066, _synthetic_keypoints(170.0)),
    ]
    _write_clip(clip, records)
    assert replay(clip) == 0


def test_replay_is_deterministic(tmp_path: Path):
    clip = tmp_path / "three.jsonl"
    _write_clip(clip, _angle_sweep(n_reps=3))
    assert replay(clip) == replay(clip) == replay(clip)


def test_replay_missing_required_keypoint_is_skipped(tmp_path: Path):
    clip = tmp_path / "partial.jsonl"
    record = build_record(0.0, _synthetic_keypoints(170.0))
    del record["keypoints"]["RIGHT_ANKLE"]
    _write_clip(clip, [record])
    assert replay(clip) == 0
