import asyncio
import random
from datetime import datetime, timezone

from config import (
    CAMERAS,
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    DETECTION_INTERVAL_MAX,
    DETECTION_INTERVAL_MIN,
    DETECTION_TYPES,
)
from websocket_manager import manager


def _make_event(cam_id: str) -> dict:
    x = round(random.uniform(0.05, 0.70), 3)
    y = round(random.uniform(0.05, 0.70), 3)
    w = round(random.uniform(0.10, 0.25), 3)
    h = round(random.uniform(0.10, 0.25), 3)
    return {
        "camera_id": cam_id,
        "event_type": random.choice(DETECTION_TYPES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "confidence": round(random.uniform(CONFIDENCE_MIN, CONFIDENCE_MAX), 3),
        "bounding_box": {"x": x, "y": y, "width": w, "height": h},
    }


async def detection_loop() -> None:
    cam_ids = [c["id"] for c in CAMERAS]
    while True:
        await asyncio.sleep(random.uniform(DETECTION_INTERVAL_MIN, DETECTION_INTERVAL_MAX))
        event = _make_event(random.choice(cam_ids))
        await manager.broadcast(event)
