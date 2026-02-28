import asyncio
from typing import AsyncGenerator

import cv2
import numpy as np

from camera_manager import CameraCapture
from config import MJPEG_FPS_TARGET

FRAME_INTERVAL = 1.0 / MJPEG_FPS_TARGET

# Pre-render a black placeholder frame for offline cameras
_black = np.zeros((480, 640, 3), dtype=np.uint8)
_, _black_buf = cv2.imencode(".jpg", _black)
OFFLINE_FRAME = bytes(_black_buf)


def _build_mjpeg_part(jpeg_bytes: bytes) -> bytes:
    header = (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n"
        b"Content-Length: " + str(len(jpeg_bytes)).encode() + b"\r\n"
        b"\r\n"
    )
    return header + jpeg_bytes + b"\r\n"


async def mjpeg_stream(cap: CameraCapture) -> AsyncGenerator[bytes, None]:
    loop = asyncio.get_event_loop()
    while True:
        start = loop.time()

        frame_bytes = await loop.run_in_executor(None, cap.read_frame)
        if frame_bytes is None:
            frame_bytes = OFFLINE_FRAME

        yield _build_mjpeg_part(frame_bytes)

        elapsed = loop.time() - start
        await asyncio.sleep(max(0.0, FRAME_INTERVAL - elapsed))
