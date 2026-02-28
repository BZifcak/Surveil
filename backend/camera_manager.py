import threading
from pathlib import Path
from typing import Optional

import cv2

from config import CAMERAS, JPEG_QUALITY, VIDEOS_DIR
from models import CameraStatus


class CameraCapture:
    def __init__(self, video_path: Path):
        self._path = video_path
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._online = False
        self._open()

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

    @property
    def online(self) -> bool:
        return self._online

    def read_frame(self) -> Optional[bytes]:
        with self._lock:
            if not self._online or self._cap is None:
                return None
            ret, frame = self._cap.read()
            if not ret:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._cap.read()
                if not ret:
                    return None
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            return bytes(buf) if ok else None

    def release(self) -> None:
        with self._lock:
            if self._cap:
                self._cap.release()
                self._cap = None
            self._online = False


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
