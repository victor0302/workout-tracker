"""Shared JSONL record format for vision recording/replay.

Dep-free on purpose (no cv2, no mediapipe) so tests, the replay harness
and the synthetic-clip generator can import the format without pulling
the full vision-runtime dependencies.
"""

from dataclasses import dataclass


@dataclass
class Keypoint:
    x: float
    y: float
    z: float
    visibility: float


def build_record(ts: float, keypoints: dict[str, Keypoint] | None) -> dict:
    """One JSONL line's contents for a recorded frame.

    Format is the contract between vision.main's --record flag and
    vision.replay.iter_jsonl; keep them in sync.
    """
    if keypoints is None:
        return {"ts": ts, "keypoints": None}
    return {
        "ts": ts,
        "keypoints": {
            name: {"x": kp.x, "y": kp.y, "z": kp.z, "visibility": kp.visibility}
            for name, kp in keypoints.items()
        },
    }
