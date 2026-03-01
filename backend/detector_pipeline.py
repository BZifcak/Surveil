"""
detector_pipeline.py

Replaces mock_detector.py. Provides a single coroutine:
    async def detection_loop() -> None

Detectors are instantiated once at module import time (weights load at startup).
The loop round-robins through all cameras at DETECTION_FPS, running all enabled
detectors on each camera's latest frame.

To add a new detector:
    1. Create detectors/my_detector.py subclassing BaseDetector
    2. Add an instance to the _detectors list below
    3. Add a toggle to config.py if desired
"""
import asyncio
import logging

import camera_manager
from config import CAMERAS, DETECTION_FPS
from detectors import GeminiWeaponDetector, MotionDetector, PersonDetector, WeaponDetector
from websocket_manager import manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Instantiate all detectors once at import time.
# Order: Person → Motion → local YOLO weapon → Gemini (fallback, person-gated)
# WeaponDetector auto-disables if models/weapon.pt is absent.
# GeminiWeaponDetector only fires when a person is present and weapon.pt is absent.
# ---------------------------------------------------------------------------
_person_detector = PersonDetector()
_weapon_detector = WeaponDetector()
_gemini_detector = GeminiWeaponDetector()
_motion_detector = MotionDetector()

_detectors = [
    _person_detector,
    _motion_detector,
    _weapon_detector,   # fast local YOLO — no rate limit, runs every frame
    _gemini_detector,   # slow API fallback — only fires when person present
]

for _d in _detectors:
    logger.info("[pipeline] %-20s %s", _d.name, "ENABLED" if _d.enabled else "DISABLED")

_PER_CAMERA_SLEEP = 1.0 / DETECTION_FPS / max(len(CAMERAS), 1)


async def detection_loop() -> None:
    """Round-robin through cameras at DETECTION_FPS per camera.

    For each camera:
      1. Fetch the latest cached numpy frame (non-blocking).
      2. Run all enabled detectors sequentially in a thread executor.
      3. Broadcast each resulting event over WebSocket.

    Sleeping _PER_CAMERA_SLEEP between cameras spreads CPU load evenly
    instead of bursting all 9 cameras' inference in a single tick.
    """
    cam_ids = [c["id"] for c in CAMERAS]
    loop = asyncio.get_event_loop()

    logger.info(
        "[pipeline] Detection loop started — %d cameras @ %d fps "
        "(%.0f ms between cameras)",
        len(cam_ids),
        DETECTION_FPS,
        _PER_CAMERA_SLEEP * 1000,
    )

    while True:
        for cam_id in cam_ids:
            cap = camera_manager.get_capture(cam_id)
            if cap is None or not cap.online:
                await asyncio.sleep(_PER_CAMERA_SLEEP)
                continue

            frame = cap.get_latest_frame()
            if frame is None:
                # Streamer hasn't decoded a frame yet for this camera
                await asyncio.sleep(_PER_CAMERA_SLEEP)
                continue

            events = await loop.run_in_executor(
                None, _run_detectors, frame, cam_id
            )

            for event in events:
                await manager.broadcast(event)

            await asyncio.sleep(_PER_CAMERA_SLEEP)


def _run_detectors(frame, cam_id: str) -> list[dict]:
    """Synchronous — runs in thread executor so YOLO doesn't block the event loop."""
    all_events: list[dict] = []
    for detector in _detectors:
        if not detector.enabled:
            continue
        try:
            if detector is _gemini_detector:
                person_events = [e for e in all_events if e.get("event_type") == "person_detected"]
                events = detector.detect(frame, cam_id, person_events=person_events)
            else:
                events = detector.detect(frame, cam_id)
            all_events.extend(events)
        except Exception as exc:
            logger.error(
                "[pipeline] %s raised on %s: %s",
                detector.name, cam_id, exc, exc_info=True,
            )
    return all_events
