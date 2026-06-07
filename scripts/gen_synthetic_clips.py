"""Generate the Phase 1 synthetic regression set.

Run from the repo root:

    python scripts/gen_synthetic_clips.py

Re-running is deterministic — overwrites every clip in `regression_set/`
with identical bytes. Any noise is seeded.

Each clip's filename encodes its expected rep count for the regression
test (#14): `<label>_<n>reps.jsonl` → expect N reps.
"""

import json
import math
import random
import sys
from pathlib import Path

# Allow `from vision.main import ...` when running as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vision.recording import Keypoint, build_record  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "regression_set"
FPS = 30


def keypoints_for_angle(angle_deg: float) -> dict[str, Keypoint]:
    """Three keypoints constructed so joint_angle(hip, knee, ankle) == angle_deg.

    Knee at origin, hip straight up, ankle rotated `angle_deg` from the
    hip vector. The rep counter cares only about the resulting angle.
    """
    rad = math.radians(angle_deg)
    return {
        "RIGHT_HIP": Keypoint(x=0.0, y=1.0, z=0.0, visibility=1.0),
        "RIGHT_KNEE": Keypoint(x=0.0, y=0.0, z=0.0, visibility=1.0),
        "RIGHT_ANKLE": Keypoint(x=math.sin(rad), y=math.cos(rad), z=0.0, visibility=1.0),
    }


def clean_reps(n_reps: int, samples_per_rep: int = 60) -> list[dict]:
    """Clean sinusoidal squats: 170° → 70° → 170° per rep, ~2s at 30fps."""
    return [
        build_record(
            ts=(rep * samples_per_rep + i) / FPS,
            keypoints=keypoints_for_angle(
                120.0 + 50.0 * math.cos(2 * math.pi * (i / samples_per_rep))
            ),
        )
        for rep in range(n_reps)
        for i in range(samples_per_rep)
    ]


def noisy_reps(
    n_reps: int, samples_per_rep: int = 60, noise_deg: float = 2.0, seed: int = 42
) -> list[dict]:
    """Same shape as clean_reps but with ±noise_deg uniform jitter per frame."""
    rng = random.Random(seed)
    return [
        build_record(
            ts=(rep * samples_per_rep + i) / FPS,
            keypoints=keypoints_for_angle(
                120.0
                + 50.0 * math.cos(2 * math.pi * (i / samples_per_rep))
                + rng.uniform(-noise_deg, noise_deg)
            ),
        )
        for rep in range(n_reps)
        for i in range(samples_per_rep)
    ]


def standing_still(seconds: float = 5.0, angle_deg: float = 175.0) -> list[dict]:
    n = int(seconds * FPS)
    return [
        build_record(ts=t / FPS, keypoints=keypoints_for_angle(angle_deg))
        for t in range(n)
    ]


def partial_reps(n_dips: int = 3, samples_per_dip: int = 60) -> list[dict]:
    """Dips to 85° — past the down-trigger (90°) but not deep enough for a real
    squat. Naive counter counts each. Depth gate (#11) should reject them."""
    return [
        build_record(
            ts=(rep * samples_per_dip + i) / FPS,
            keypoints=keypoints_for_angle(
                127.5 + 42.5 * math.cos(2 * math.pi * (i / samples_per_dip))
            ),
        )
        for rep in range(n_dips)
        for i in range(samples_per_dip)
    ]


def jitter(n_cycles: int = 15, samples_per_cycle: int = 6) -> list[dict]:
    """Fast 200ms oscillation 170° → 60° → 170°. Deep enough to pass any depth
    gate but each cycle is too short for hysteresis (~150ms dwell) or for a
    min-duration filter (~0.8s). Naive counter over-counts; #10 and #12
    should drive this to 0."""
    return [
        build_record(
            ts=(cycle * samples_per_cycle + i) / FPS,
            keypoints=keypoints_for_angle(
                115.0 + 55.0 * math.cos(2 * math.pi * (i / samples_per_cycle))
            ),
        )
        for cycle in range(n_cycles)
        for i in range(samples_per_cycle)
    ]


CLIPS = [
    ("clean_5reps.jsonl", lambda: clean_reps(5)),
    ("clean_8reps.jsonl", lambda: clean_reps(8)),
    ("clean_10reps.jsonl", lambda: clean_reps(10)),
    ("noisy_5reps.jsonl", lambda: noisy_reps(5)),
    ("standing_0reps.jsonl", lambda: standing_still(5.0)),
    ("partial_0reps.jsonl", lambda: partial_reps(3)),
    ("jitter_0reps.jsonl", lambda: jitter(15)),
]


def write_clip(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def main() -> None:
    print(f"writing to {OUT_DIR}")
    for name, gen in CLIPS:
        path = OUT_DIR / name
        records = gen()
        write_clip(path, records)
        print(f"  {name} — {len(records)} frames")


if __name__ == "__main__":
    main()
