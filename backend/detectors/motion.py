import logging
from datetime import datetime, timezone

import cv2
import numpy as np

from config import ENABLE_MOTION_DETECTION, MOTION_MIN_AREA
from detectors.base import BaseDetector

logger = logging.getLogger(__name__)

# Small kernel: removes salt-and-pepper noise from camera shake
_NOISE_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
# Large kernel: merges nearby fragments (bus body, windows, shadow edges)
# into one big blob so the bus registers as a single large contour
_MERGE_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))


class MotionDetector(BaseDetector):
    """Detects motion using a per-camera MOG2 background subtractor.

    No model weights required — pure OpenCV.
    Toggle via ENABLE_MOTION_DETECTION in config.py.
    """

    def __init__(self) -> None:
        self._subtractors: dict[str, cv2.BackgroundSubtractorMOG2] = {}
        logger.info(
            "[MotionDetector] Ready (min_area=%d px²)", MOTION_MIN_AREA
        )

    @property
    def name(self) -> str:
        return "motion_detector"

    @property
    def enabled(self) -> bool:
        return ENABLE_MOTION_DETECTION

    def _subtractor(self, cam_id: str) -> cv2.BackgroundSubtractorMOG2:
        if cam_id not in self._subtractors:
            self._subtractors[cam_id] = cv2.createBackgroundSubtractorMOG2(
                history=500,
                varThreshold=25,     # higher = less sensitive to camera shake
                detectShadows=False,
            )
        return self._subtractors[cam_id]

    def detect(self, frame: np.ndarray, cam_id: str) -> list[dict]:
        if not self.enabled:
            return []
        h, w = frame.shape[:2]

        fg_mask = self._subtractor(cam_id).apply(frame, learningRate=-1)

        # Step 1: remove tiny noise specks from camera shake
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, _NOISE_KERNEL)

        # Step 2: dilate heavily to merge fragmented object parts
        # (bus body + windows + shadow edges → one solid blob)
        fg_mask = cv2.dilate(fg_mask, _MERGE_KERNEL, iterations=2)

        # Step 3: fill any remaining holes inside blobs
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, _MERGE_KERNEL)

        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        events: list[dict] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < MOTION_MIN_AREA:
                continue
            px, py, cw, ch = cv2.boundingRect(contour)
            confidence = min(0.95, area / (w * h) * 20)
            events.append({
                "camera_id": cam_id,
                "event_type": "motion",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": round(confidence, 3),
                "bounding_box": {
                    "x":      round(px / w, 4),
                    "y":      round(py / h, 4),
                    "width":  round(cw / w, 4),
                    "height": round(ch / h, 4),
                },
            })
        return events
