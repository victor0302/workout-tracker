"""Vision tracker entrypoint.

Captures frames from a webcam or file, runs MediaPipe pose, drives the
rep counter off the averaged knee angle, asks the classifier what
exercise is happening, and POSTs running totals to the dashboard.
"""

import argparse
import json
import time
from pathlib import Path
from typing import IO

import cv2
import requests

from .exercise_classifier import ExerciseClassifier
from .pose_estimator import PoseEstimator
from .recording import build_record
from .rep_counter import RepCounter
from .signal import knee_angle

DASHBOARD_URL = "http://localhost:8000/ingest/vision"


def build_vision_payload(exercise: str, reps: int, angle: float) -> dict:
    """The exact payload shape this tracker sends to /ingest/vision.

    Extracted so contract tests can verify the dashboard accepts what
    vision sends without spinning up a real webcam.
    """
    return {"exercise": exercise, "reps": reps, "angle": angle}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="0", help="webcam index or path to video file")
    p.add_argument("--dashboard", default=DASHBOARD_URL)
    p.add_argument("--no-display", action="store_true")
    p.add_argument(
        "--record",
        type=Path,
        default=None,
        help="JSONL path to record keypoints to (off if omitted)",
    )
    return p.parse_args()


def open_source(src: str) -> cv2.VideoCapture:
    return cv2.VideoCapture(int(src)) if src.isdigit() else cv2.VideoCapture(src)


def main() -> None:
    args = parse_args()
    cap = open_source(args.source)
    if not cap.isOpened():
        raise SystemExit(f"could not open video source {args.source!r}")

    pose = PoseEstimator()
    classifier = ExerciseClassifier()
    # Knee angle ranges for a squat-ish placeholder signal.
    counter = RepCounter(down_threshold=90.0, up_threshold=160.0)

    record_file: IO[str] | None = args.record.open("w") if args.record else None

    last_post = 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            keypoints = pose.process(frame)
            if record_file is not None:
                record_file.write(json.dumps(build_record(time.time(), keypoints)) + "\n")

            angle = knee_angle(keypoints) if keypoints is not None else None
            if angle is not None:
                reps = counter.update(angle)
                exercise = classifier.update(keypoints)

                if not args.no_display:
                    cv2.putText(
                        frame,
                        f"{exercise} reps={reps} angle={angle:.0f}",
                        (12, 32),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0),
                        2,
                    )

                now = time.time()
                if now - last_post > 1.0:
                    try:
                        requests.post(
                            args.dashboard,
                            json=build_vision_payload(exercise, reps, angle),
                            timeout=0.5,
                        )
                    except requests.RequestException:
                        pass
                    last_post = now

            if not args.no_display:
                cv2.imshow("workout-tracker", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        if record_file is not None:
            record_file.close()
        cap.release()
        cv2.destroyAllWindows()
        pose.close()


if __name__ == "__main__":
    main()
