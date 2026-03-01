import logging
from datetime import datetime, timezone

import numpy as np
from ultralytics import YOLO

from config import (
    DETECTION_DEVICE,
    ENABLE_WEAPON_DETECTION,
    MODEL_DIR,
    WEAPON_CONFIDENCE_THRESHOLD,
)
from detectors.base import BaseDetector

logger = logging.getLogger(__name__)

_WEIGHTS = MODEL_DIR / "weapon.pt"


class WeaponDetector(BaseDetector):
    """Detects weapons using a YOLO11n model trained on real CCTV footage.

    Weights live at backend/models/weapon.pt (not committed — drop in manually).
    Train with: python train_weapon_detector.py --images-dir Images --train
    (Uses Pascal VOC XML bounding box annotations — no auto-annotation needed.)

    Falls back gracefully (disabled) if weapon.pt is not present.
    """

    def __init__(self) -> None:
        self._model = None
        self._enabled = False

        if not ENABLE_WEAPON_DETECTION:
            logger.info("[WeaponDetector] DISABLED via config toggle")
            return

        if not _WEIGHTS.exists():
            logger.warning(
                "[WeaponDetector] DISABLED — weapon.pt not found at %s. "
                "Train it with: python train_weapon_detector.py --images-dir Images --train",
                _WEIGHTS,
            )
            return

        logger.info(
            "[WeaponDetector] Loading %s (device=%s)...",
            _WEIGHTS,
            DETECTION_DEVICE,
        )
        self._model = YOLO(str(_WEIGHTS))
        self._model.to(DETECTION_DEVICE)
        self._enabled = True
        logger.info(
            "[WeaponDetector] Ready (confidence threshold=%.2f)",
            WEAPON_CONFIDENCE_THRESHOLD,
        )

    @property
    def name(self) -> str:
        return "weapon_detector"

    @property
    def enabled(self) -> bool:
        return self._enabled

    # Cameras excluded from weapon detection (0-indexed: cam_10 = Camera 11)
    _SKIP_CAMERAS = {"cam_10", "cam_3"}

    def detect(self, frame: np.ndarray, cam_id: str) -> list[dict]:
        if not self.enabled or self._model is None:
            return []
        if cam_id in self._SKIP_CAMERAS:
            return []

        h, w = frame.shape[:2]
        results = self._model(
            frame,
            conf=WEAPON_CONFIDENCE_THRESHOLD,
            verbose=False,
        )

        events: list[dict] = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cls_id = int(box.cls[0])
                cls_name = (result.names or {}).get(cls_id, "weapon")
                events.append(
                    {
                        "camera_id": cam_id,
                        "event_type": "weapon_detected",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "confidence": round(float(box.conf[0]), 3),
                        "weapon_type": cls_name,
                        "bounding_box": {
                            "x": round(x1 / w, 4),
                            "y": round(y1 / h, 4),
                            "width": round((x2 - x1) / w, 4),
                            "height": round((y2 - y1) / h, 4),
                        },
                    }
                )

        if events:
            logger.info(
                "[WeaponDetector] %d weapon(s) on %s: %s",
                len(events),
                cam_id,
                [e["weapon_type"] for e in events],
            )

        return events
