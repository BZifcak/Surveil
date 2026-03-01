import json
import logging
import os
import time
from datetime import datetime, timezone

import cv2
import numpy as np

from config import ENABLE_WEAPON_DETECTION, GEMINI_WEAPON_COOLDOWN_SECS
from detectors.base import BaseDetector

logger = logging.getLogger(__name__)


def _build_prompt(person_events: list[dict] | None) -> str:
    if person_events:
        n = len(person_events)
        bbox_strs = [
            f"(x={e['bounding_box']['x']:.2f}, y={e['bounding_box']['y']:.2f}, "
            f"w={e['bounding_box']['width']:.2f}, h={e['bounding_box']['height']:.2f})"
            for e in person_events
        ]
        person_ctx = (
            f"A person detector found {n} person(s) at these normalized positions: "
            + ", ".join(bbox_strs)
            + ". Pay special attention to whether any of these people are holding a weapon. "
            "Also scan the rest of the frame for unattended weapons."
        )
    else:
        person_ctx = (
            "No people were detected in this frame. "
            "Scan for any unattended or dropped weapons."
        )

    return f"""You are a security surveillance AI analyzing a real CCTV camera frame.

{person_ctx}

Detect any visible weapons: handguns, pistols, rifles, shotguns, knives, machetes, or other dangerous weapons. This is real CCTV footage — it may be grainy, low-resolution, or shot from an overhead angle. Flag weapons you can identify even with partial visibility or low image quality.

Do NOT flag: umbrellas, walking sticks, tripods, cameras, tools, extension cords, or other non-weapon objects.

For each weapon, set "held" to true if a person appears to be holding it, false if it looks unattended (dropped, left behind, etc.).

Respond ONLY with valid JSON, no markdown, no other text:
{{"weapons": [{{"type": "handgun", "confidence": 0.9, "held": true, "box": {{"x": 0.1, "y": 0.2, "width": 0.05, "height": 0.1}}}}]}}

Box values are normalized 0.0–1.0 (top-left origin).
If NO weapons are visible, respond with exactly: {{"weapons": []}}"""


class GeminiWeaponDetector(BaseDetector):
    """Detects weapons using Gemini 2.0 Flash vision API (google-genai SDK).

    No local model weights required. Requires GEMINI_API_KEY environment variable.
    Rate-limited globally via GEMINI_WEAPON_COOLDOWN_SECS — at most one call per
    cooldown window across ALL cameras combined, respecting the 2 RPM free-tier limit.

    pip install google-genai
    export GEMINI_API_KEY=your_key_here
    """

    def __init__(self) -> None:
        self._client = None
        self._enabled = False
        self._last_call: dict[str, float] = {}  # per-camera cooldown

        if not ENABLE_WEAPON_DETECTION:
            logger.info("[GeminiWeaponDetector] DISABLED via config toggle")
            return

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning(
                "[GeminiWeaponDetector] DISABLED — set GEMINI_API_KEY env var to enable. "
                "Get a free key at aistudio.google.com"
            )
            return

        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            self._enabled = True
            logger.info(
                "[GeminiWeaponDetector] Ready (model=gemini-2.0-flash, "
                "per-camera cooldown=%.0fs, person-gated)",
                GEMINI_WEAPON_COOLDOWN_SECS,
            )
        except ImportError:
            logger.error(
                "[GeminiWeaponDetector] google-genai not installed — "
                "run: pip install google-genai"
            )
        except Exception as exc:
            logger.error("[GeminiWeaponDetector] Failed to initialize: %s", exc)

    @property
    def name(self) -> str:
        return "gemini_weapon_detector"

    @property
    def enabled(self) -> bool:
        return self._enabled

    def detect(
        self, frame: np.ndarray, cam_id: str, person_events: list[dict] | None = None
    ) -> list[dict]:
        if not self._enabled or self._client is None:
            return []

        # Person-gated: skip entirely if YOLO found no people in this frame.
        # Empty frames never cost an API call; Gemini only fires when there's
        # someone to potentially be holding a weapon.
        if not person_events:
            return []

        # Per-camera rate limit — prevents hammering the API while a person
        # stays in frame. 30s cooldown ≈ 2 RPM per active camera.
        now = time.monotonic()
        if now - self._last_call.get(cam_id, 0) < GEMINI_WEAPON_COOLDOWN_SECS:
            return []
        self._last_call[cam_id] = now

        # Resize to 1280px wide max — saves tokens, Gemini handles it fine
        h, w = frame.shape[:2]
        if w > 1280:
            scale = 1280 / w
            frame = cv2.resize(frame, (1280, int(h * scale)))

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        image_bytes = buf.tobytes()

        prompt = _build_prompt(person_events)

        try:
            from google.genai import types
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, image_part],
            )
            text = response.text.strip()
            # Strip markdown code fences if Gemini wraps its output
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
            weapons = data.get("weapons", [])
        except Exception as exc:
            logger.debug("[GeminiWeaponDetector] API/parse error on %s: %s", cam_id, exc)
            return []

        events = []
        for weapon in weapons:
            box = weapon.get("box", {})
            events.append({
                "camera_id": cam_id,
                "event_type": "weapon_detected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": round(float(weapon.get("confidence", 0.8)), 3),
                "weapon_type": weapon.get("type", "unknown"),
                "held": bool(weapon.get("held", False)),
                "bounding_box": {
                    "x":      round(float(box.get("x", 0.0)), 4),
                    "y":      round(float(box.get("y", 0.0)), 4),
                    "width":  round(float(box.get("width", 0.1)), 4),
                    "height": round(float(box.get("height", 0.1)), 4),
                },
            })

        if events:
            logger.info(
                "[GeminiWeaponDetector] %d weapon(s) on %s: %s",
                len(events), cam_id,
                [e["weapon_type"] for e in events],
            )

        return events
