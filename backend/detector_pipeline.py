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
from detectors import FightDetector, MotionDetector, PersonDetector, WeaponDetector
from websocket_manager import manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Instantiate all detectors once at import time.
# Order: Person → Fight → Motion → Weapon (local YOLO)
# WeaponDetector auto-disables if models/weapon.pt is absent.
# ---------------------------------------------------------------------------
_person_detector = PersonDetector()
_fight_detector = FightDetector()
_weapon_detector = WeaponDetector()
_motion_detector = MotionDetector()

_detectors = [
    _person_detector,
    _fight_detector,    # pose model — person events ORed with person_detector, + fight heuristics
    _motion_detector,
    _weapon_detector,   # fast local YOLO — no rate limit, runs every frame
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


_PERSON_DEDUP_IOU_THRESHOLD = 0.5


def _deduplicate_person_events(events: list[dict]) -> list[dict]:
    """OR-merge person_detected events from PersonDetector and FightDetector.

    For overlapping detections (IoU > threshold), keep the higher confidence one.
    """
    person_events = [e for e in events if e.get("event_type") == "person_detected"]
    other_events = [e for e in events if e.get("event_type") != "person_detected"]

    if len(person_events) <= 1:
        for e in person_events:
            e.pop("source", None)
        return other_events + person_events

    def _to_xyxy(bb: dict) -> tuple:
        return (bb["x"], bb["y"], bb["x"] + bb["width"], bb["y"] + bb["height"])

    indexed = [(e, _to_xyxy(e["bounding_box"])) for e in person_events]

    suppressed = set()
    for i in range(len(indexed)):
        if i in suppressed:
            continue
        for j in range(i + 1, len(indexed)):
            if j in suppressed:
                continue
            iou = _compute_iou(indexed[i][1], indexed[j][1])
            if iou > _PERSON_DEDUP_IOU_THRESHOLD:
                if indexed[i][0]["confidence"] >= indexed[j][0]["confidence"]:
                    suppressed.add(j)
                else:
                    suppressed.add(i)
                    break

    kept = [indexed[k][0] for k in range(len(indexed)) if k not in suppressed]
    for e in kept:
        e.pop("source", None)

    return other_events + kept


def _compute_iou(box_a: tuple, box_b: tuple) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union > 1e-8 else 0.0


def _run_detectors(frame, cam_id: str) -> list[dict]:
    """Synchronous — runs in thread executor so YOLO doesn't block the event loop."""
    all_events: list[dict] = []
    for detector in _detectors:
        if not detector.enabled:
            continue
        try:
            events = detector.detect(frame, cam_id)
            all_events.extend(events)

            # After FightDetector, deduplicate person events so downstream
            # detectors see the clean merged person list
            if detector is _fight_detector:
                all_events = _deduplicate_person_events(all_events)
        except Exception as exc:
            logger.error(
                "[pipeline] %s raised on %s: %s",
                detector.name, cam_id, exc, exc_info=True,
            )
    return all_events
