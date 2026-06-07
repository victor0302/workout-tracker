"""Thin wrapper around MediaPipe Pose."""

import mediapipe as mp
import numpy as np

from .recording import Keypoint


class PoseEstimator:
    def __init__(self, model_complexity: int = 1, min_detection_confidence: float = 0.5):
        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=0.5,
        )
        self.landmark_names = [lm.name for lm in self._mp_pose.PoseLandmark]

    def process(self, frame_bgr: np.ndarray) -> dict[str, Keypoint] | None:
        frame_rgb = frame_bgr[:, :, ::-1]
        result = self._pose.process(frame_rgb)
        if not result.pose_landmarks:
            return None
        return {
            name: Keypoint(lm.x, lm.y, lm.z, lm.visibility)
            for name, lm in zip(self.landmark_names, result.pose_landmarks.landmark)
        }

    def close(self) -> None:
        self._pose.close()
