import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from config import CAMERAS, JPEG_QUALITY, MJPEG_FPS_TARGET, VIDEOS_DIR
from models import CameraStatus


class CameraCapture:
    def __init__(self, video_path: Path):
        self._path = video_path
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._online = False
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_jpeg: Optional[bytes] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._open()
        if self._online:
            self._start_decode_thread()

    def _open(self) -> None:
        if not self._path.exists():
            self._online = False
            return
        cap = cv2.VideoCapture(str(self._path))
        if cap.isOpened():
            self._cap = cap
            self._online = True
        else:
            self._online = False

    def _start_decode_thread(self) -> None:
        fps = MJPEG_FPS_TARGET
        if self._cap is not None:
            native_fps = self._cap.get(cv2.CAP_PROP_FPS)
            if native_fps > 0:
                fps = native_fps
        self._target_interval = 1.0 / fps
        self._thread = threading.Thread(target=self._decode_loop, daemon=True)
        self._thread.start()

    def _decode_loop(self) -> None:
        while not self._stop.is_set():
            start = time.monotonic()
            with self._lock:
                if not self._online or self._cap is None:
                    break
                ret, frame = self._cap.read()
                if not ret:
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self._cap.read()
                    if not ret:
                        break
                self._latest_frame = frame
                ok, buf = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
                )
                if ok:
                    self._latest_jpeg = bytes(buf)
            elapsed = time.monotonic() - start
            sleep_time = self._target_interval - elapsed
            if sleep_time > 0:
                self._stop.wait(sleep_time)

    @property
    def online(self) -> bool:
        return self._online

    def read_frame(self) -> Optional[bytes]:
        """Return the latest cached JPEG snapshot."""
        with self._lock:
            return self._latest_jpeg

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Return a copy of the most recently decoded frame as a numpy array."""
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def release(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        with self._lock:
            if self._cap:
                self._cap.release()
                self._cap = None
            self._online = False
            self._latest_frame = None
            self._latest_jpeg = None


_captures: dict[str, CameraCapture] = {}


def init_cameras() -> None:
    for cam in CAMERAS:
        path = VIDEOS_DIR / f"{cam['id']}.mp4"
        _captures[cam["id"]] = CameraCapture(path)


def get_capture(cam_id: str) -> Optional[CameraCapture]:
    return _captures.get(cam_id)


def get_all_statuses() -> list[CameraStatus]:
    return [
        CameraStatus(
            id=cam["id"],
            name=cam["name"],
            location=cam["location"],
            status="online" if _captures[cam["id"]].online else "offline",
            stream_url=f"/stream/{cam['id']}",
        )
        for cam in CAMERAS
    ]


def shutdown_cameras() -> None:
    for cap in _captures.values():
        cap.release()
