"""Replay a recorded keypoint stream through the rep counter, headless.

JSONL format (one record per line, must match `vision.recording.build_record`):

    {"ts": float, "keypoints": null}
    {"ts": float, "keypoints": {"<NAME>": {"x": .., "y": .., "z": .., "visibility": ..}, ...}}

Null-keypoint lines are skipped (the camera saw the frame but pose
detection failed). Replay is deterministic: same clip + same counter
settings always produces the same count.
"""

import argparse
import json
from collections.abc import Iterator
from pathlib import Path

from .pose_estimator import joint_angle
from .recording import Keypoint
from .rep_counter import RepCounter


def _default_counter() -> RepCounter:
    # Same thresholds main.py uses today; later Phase 1 tickets will tune these.
    return RepCounter(down_threshold=90.0, up_threshold=160.0)


def iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _kp_from_dict(raw: dict | None) -> dict[str, Keypoint] | None:
    if raw is None:
        return None
    return {name: Keypoint(**vals) for name, vals in raw.items()}


def replay(path: Path, counter: RepCounter | None = None) -> int:
    """Replay a JSONL clip through the rep counter; return total rep count."""
    counter = counter or _default_counter()
    for record in iter_jsonl(path):
        kp = _kp_from_dict(record.get("keypoints"))
        if kp is None:
            continue
        hip, knee, ankle = kp.get("RIGHT_HIP"), kp.get("RIGHT_KNEE"), kp.get("RIGHT_ANKLE")
        if not (hip and knee and ankle):
            continue
        angle = joint_angle(hip, knee, ankle)
        counter.update(angle)
    return counter.count


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("path", type=Path, help="JSONL clip to replay")
    args = p.parse_args()
    if not args.path.exists():
        raise SystemExit(f"clip not found: {args.path}")
    print(f"reps: {replay(args.path)}")


if __name__ == "__main__":
    main()
