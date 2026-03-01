import logging
from datetime import datetime, timezone

import numpy as np
from ultralytics import YOLO

from config import DETECTION_DEVICE, ENABLE_PERSON_DETECTION, MODEL_DIR, PERSON_CONFIDENCE_THRESHOLD
from detectors.base import BaseDetector

logger = logging.getLogger(__name__)

_COCO_PERSON_CLASS = 0  # class index 0 is "person" in COCO 80-class set


_WEIGHTS = MODEL_DIR / "yolo11s.pt"


class PersonDetector(BaseDetector):
    """Detects people using YOLO11s trained on COCO.

    Weights stored at backend/models/yolo11s.pt.
    Toggle via ENABLE_PERSON_DETECTION in config.py.
    """

    def __init__(self) -> None:
        if not ENABLE_PERSON_DETECTION:
            logger.info("[PersonDetector] DISABLED via config")
            self._model = None
            return
        logger.info("[PersonDetector] Loading %s (device=%s)...", _WEIGHTS, DETECTION_DEVICE)
        self._model = YOLO(str(_WEIGHTS))
        self._model.to(DETECTION_DEVICE)
        logger.info(
            "[PersonDetector] Ready (confidence threshold=%.2f)",
            PERSON_CONFIDENCE_THRESHOLD,
        )

    @property
    def name(self) -> str:
        return "person_detector"

    @property
    def enabled(self) -> bool:
        return ENABLE_PERSON_DETECTION and self._model is not None

    def detect(self, frame: np.ndarray, cam_id: str) -> list[dict]:
        if not self.enabled:
            return []
        h, w = frame.shape[:2]
        results = self._model(
            frame,
            conf=PERSON_CONFIDENCE_THRESHOLD,
            classes=[_COCO_PERSON_CLASS],
            verbose=False,
        )
        events: list[dict] = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                events.append({
                    "camera_id": cam_id,
                    "event_type": "person_detected",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "confidence": round(float(box.conf[0]), 3),
                    "bounding_box": {
                        "x":      round(x1 / w, 4),
                        "y":      round(y1 / h, 4),
                        "width":  round((x2 - x1) / w, 4),
                        "height": round((y2 - y1) / h, 4),
                    },
                })
        return events
