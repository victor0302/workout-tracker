"""Vision tracker entrypoint.

Captures frames from a webcam or file, runs MediaPipe pose, drives the
rep counter off the right-knee angle (placeholder signal for "squat"),
asks the classifier what exercise is happening, and POSTs running
totals to the dashboard.
"""

import argparse
import time

import cv2
import requests

from .exercise_classifier import ExerciseClassifier
from .pose_estimator import PoseEstimator, joint_angle
from .rep_counter import RepCounter

DASHBOARD_URL = "http://localhost:8000/ingest/vision"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="0", help="webcam index or path to video file")
    p.add_argument("--dashboard", default=DASHBOARD_URL)
    p.add_argument("--no-display", action="store_true")
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

    last_post = 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            keypoints = pose.process(frame)
            if keypoints is not None:
                hip = keypoints["RIGHT_HIP"]
                knee = keypoints["RIGHT_KNEE"]
                ankle = keypoints["RIGHT_ANKLE"]
                angle = joint_angle(hip, knee, ankle)

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
                            json={"exercise": exercise, "reps": reps, "angle": angle},
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
        cap.release()
        cv2.destroyAllWindows()
        pose.close()


if __name__ == "__main__":
    main()
