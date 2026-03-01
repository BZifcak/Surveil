from abc import ABC, abstractmethod

import numpy as np


class BaseDetector(ABC):
    """Abstract base for all detection models.

    To add a new detector: subclass this, implement name + detect(),
    and add an instance to the _detectors list in detector_pipeline.py.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier used in logs and error messages."""
        ...

    @property
    def enabled(self) -> bool:
        """Whether this detector should run. Override to False when weights
        are unavailable or the demo toggle is off."""
        return True

    @abstractmethod
    def detect(self, frame: np.ndarray, cam_id: str) -> list[dict]:
        """Run detection on a single BGR numpy frame.

        Args:
            frame:  HxWx3 BGR uint8 numpy array (OpenCV native format).
            cam_id: Camera ID string (e.g. "cam_0"), used to scope
                    per-camera state such as MOG2 background models.

        Returns:
            List of event dicts. Each must match the DetectionEvent schema:
            {camera_id, event_type, timestamp (ISO-8601), confidence (0-1),
             bounding_box: {x, y, width, height} all normalised 0-1}.
            Return [] when nothing is detected.
        """
        ...
