import asyncio
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import camera_manager
import mock_detector
from config import ALLOWED_ORIGINS, CAMERAS
from models import CameraStatus
from streamer import mjpeg_stream
from websocket_manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    camera_manager.init_cameras()
    detector_task = asyncio.create_task(mock_detector.detection_loop())
    yield
    detector_task.cancel()
    try:
        await detector_task
    except asyncio.CancelledError:
        pass
    camera_manager.shutdown_cameras()


app = FastAPI(title="Surveil API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_CAM_IDS = {c["id"] for c in CAMERAS}


def _require_cam(cam_id: str):
    if cam_id not in VALID_CAM_IDS:
        raise HTTPException(status_code=404, detail=f"Camera '{cam_id}' not found")
    return camera_manager.get_capture(cam_id)


@app.get("/cameras", response_model=List[CameraStatus])
async def list_cameras():
    return camera_manager.get_all_statuses()


@app.get("/stream/{cam_id}")
async def stream_camera(cam_id: str):
    cap = _require_cam(cam_id)
    return StreamingResponse(
        mjpeg_stream(cap),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.websocket("/ws/events")
async def websocket_events(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(ws)
