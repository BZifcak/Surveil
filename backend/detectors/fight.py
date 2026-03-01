"""
fight.py — Fight detection via YOLOv8-pose keypoint heuristics.

Loads yolov8n-pose.pt (auto-downloads from Ultralytics hub on first run).
Produces:
  - person_detected events (ORed with PersonDetector in the pipeline)
  - fight_detected events when heuristic criteria are met between 2+ people

False-positive reduction:
  - Proximity is a mandatory gate (can't fight from far away)
  - Criteria must sustain across FIGHT_SUSTAIN_FRAMES consecutive frames
"""
import logging
import time
from collections import deque
from datetime import datetime, timezone
from itertools import combinations

import numpy as np
from ultralytics import YOLO

from config import (
    DETECTION_DEVICE,
    ENABLE_FIGHT_DETECTION,
    FIGHT_ARM_INTRUSION_MARGIN,
    FIGHT_EVENT_COOLDOWN_SECS,
    FIGHT_KEYPOINT_CONFIDENCE_MIN,
    FIGHT_MIN_CRITERIA,
    FIGHT_POSE_CONFIDENCE_THRESHOLD,
    FIGHT_PROXIMITY_RATIO,
    FIGHT_SUSTAIN_FRAMES,
    FIGHT_VELOCITY_THRESHOLD,
)
from detectors.base import BaseDetector

logger = logging.getLogger(__name__)

# COCO 17-keypoint indices
_WRIST_INDICES = [9, 10]   # left_wrist, right_wrist
_ELBOW_INDICES = [7, 8]    # left_elbow, right_elbow
_LIMB_INDICES = _WRIST_INDICES + _ELBOW_INDICES

# (wrist_idx, shoulder_idx) pairs for aggressive-posture check
_WRIST_SHOULDER_PAIRS = [(9, 5), (10, 6)]

_COCO_PERSON_CLASS = 0


class _PersonPose:
    """Intermediate representation for one detected person in a frame."""
    __slots__ = ("bbox_norm", "bbox_xyxy_norm", "center", "diagonal",
                 "keypoints_norm", "keypoints_conf", "confidence")

    def __init__(self, bbox_norm: dict, bbox_xyxy_norm: tuple,
                 keypoints_norm: np.ndarray, keypoints_conf: np.ndarray,
                 confidence: float):
        self.bbox_norm = bbox_norm
        self.bbox_xyxy_norm = bbox_xyxy_norm
        x1, y1, x2, y2 = bbox_xyxy_norm
        self.center = ((x1 + x2) / 2, (y1 + y2) / 2)
        self.diagonal = np.hypot(x2 - x1, y2 - y1)
        self.keypoints_norm = keypoints_norm  # (17, 2) normalized x, y
        self.keypoints_conf = keypoints_conf  # (17,)
        self.confidence = confidence


class FightDetector(BaseDetector):
    """Detects fights between people using YOLOv8n-pose keypoint heuristics.

    Model: yolov8n-pose.pt (auto-downloads from Ultralytics hub).
    Toggle via ENABLE_FIGHT_DETECTION in config.py.
    """

    def __init__(self) -> None:
        self._model = None
        self._prev_keypoints: dict[str, list[np.ndarray]] = {}
        self._prev_bboxes: dict[str, list[tuple]] = {}
        self._last_fight_time: dict[str, float] = {}
        # Stable slot IDs for tracking people across frames (per camera)
        self._next_slot: dict[str, int] = {}
        self._prev_slots: dict[str, list[int]] = {}  # cam_id -> list of slot IDs
        # Temporal accumulation: cam_id -> {(slot_a, slot_b) -> deque of bools}
        self._fight_history: dict[str, dict[tuple[int, int], deque]] = {}

        if not ENABLE_FIGHT_DETECTION:
            logger.info("[FightDetector] DISABLED via config")
            return

        logger.info("[FightDetector] Loading yolov8n-pose.pt (device=%s)...", DETECTION_DEVICE)
        self._model = YOLO("yolov8n-pose.pt")
        self._model.to(DETECTION_DEVICE)
        logger.info(
            "[FightDetector] Ready (pose_conf=%.2f, min_criteria=%d)",
            FIGHT_POSE_CONFIDENCE_THRESHOLD,
            FIGHT_MIN_CRITERIA,
        )

    @property
    def name(self) -> str:
        return "fight_detector"

    @property
    def enabled(self) -> bool:
        return ENABLE_FIGHT_DETECTION and self._model is not None

    def detect(self, frame: np.ndarray, cam_id: str) -> list[dict]:
        if not self.enabled:
            return []

        h, w = frame.shape[:2]
        results = self._model(
            frame,
            conf=FIGHT_POSE_CONFIDENCE_THRESHOLD,
            verbose=False,
        )

        poses: list[_PersonPose] = []
        person_events: list[dict] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for result in results:
            if result.keypoints is None or result.boxes is None:
                continue
            kp_data = result.keypoints.data  # (N, 17, 3)
            boxes = result.boxes

            for i, box in enumerate(boxes):
                if int(box.cls[0]) != _COCO_PERSON_CLASS:
                    continue

                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                bbox_norm = {
                    "x":      round(x1 / w, 4),
                    "y":      round(y1 / h, 4),
                    "width":  round((x2 - x1) / w, 4),
                    "height": round((y2 - y1) / h, 4),
                }
                bbox_xyxy_norm = (x1 / w, y1 / h, x2 / w, y2 / h)

                person_events.append({
                    "camera_id": cam_id,
                    "event_type": "person_detected",
                    "timestamp": now_iso,
                    "confidence": round(conf, 3),
                    "bounding_box": bbox_norm,
                    "source": "fight_detector",
                })

                if i < kp_data.shape[0]:
                    kp = kp_data[i].cpu().numpy()  # (17, 3)
                    kp_xy = kp[:, :2].copy()
                    kp_xy[:, 0] /= w
                    kp_xy[:, 1] /= h
                    kp_conf = kp[:, 2]
                    poses.append(_PersonPose(
                        bbox_norm=bbox_norm,
                        bbox_xyxy_norm=bbox_xyxy_norm,
                        keypoints_norm=kp_xy,
                        keypoints_conf=kp_conf,
                        confidence=conf,
                    ))

        # --- Assign stable slot IDs via IoU matching to previous frame ---
        slots = self._assign_slots(cam_id, poses)

        # --- Fight heuristic analysis (requires 2+ people with poses) ---
        fight_events: list[dict] = []

        # Init history for this camera if needed
        if cam_id not in self._fight_history:
            self._fight_history[cam_id] = {}
        history = self._fight_history[cam_id]

        # Track which pair keys are active this frame
        active_pairs: set[tuple[int, int]] = set()

        if len(poses) >= 2:
            velocities = self._compute_velocities(cam_id, poses)

            for idx_a, idx_b in combinations(range(len(poses)), 2):
                pa, pb = poses[idx_a], poses[idx_b]

                # Proximity is mandatory — skip pair if not close
                if not self._check_proximity(pa, pb):
                    continue

                # Count remaining 3 criteria
                criteria_met = 0
                criteria_details = []

                if self._check_arm_intrusion(pa, pb):
                    criteria_met += 1
                    criteria_details.append("arm_intrusion")

                vel_a = velocities[idx_a] if velocities else 0.0
                vel_b = velocities[idx_b] if velocities else 0.0
                if max(vel_a, vel_b) > FIGHT_VELOCITY_THRESHOLD:
                    criteria_met += 1
                    criteria_details.append("rapid_movement")

                if self._check_aggressive_posture(pa) or self._check_aggressive_posture(pb):
                    criteria_met += 1
                    criteria_details.append("aggressive_posture")

                passed = criteria_met >= FIGHT_MIN_CRITERIA

                # Push to temporal ring buffer for this pair
                pair_key = (min(slots[idx_a], slots[idx_b]),
                            max(slots[idx_a], slots[idx_b]))
                active_pairs.add(pair_key)

                if pair_key not in history:
                    history[pair_key] = deque(maxlen=FIGHT_SUSTAIN_FRAMES)
                history[pair_key].append(passed)

                # Only fire if sustained across FIGHT_SUSTAIN_FRAMES consecutive frames
                buf = history[pair_key]
                if len(buf) == FIGHT_SUSTAIN_FRAMES and all(buf):
                    now_mono = time.monotonic()
                    if now_mono - self._last_fight_time.get(cam_id, 0) >= FIGHT_EVENT_COOLDOWN_SECS:
                        self._last_fight_time[cam_id] = now_mono
                        base_conf = min(pa.confidence, pb.confidence)
                        fight_conf = min(0.95, base_conf + (criteria_met - FIGHT_MIN_CRITERIA) * 0.15)

                        merged_x1 = min(pa.bbox_xyxy_norm[0], pb.bbox_xyxy_norm[0])
                        merged_y1 = min(pa.bbox_xyxy_norm[1], pb.bbox_xyxy_norm[1])
                        merged_x2 = max(pa.bbox_xyxy_norm[2], pb.bbox_xyxy_norm[2])
                        merged_y2 = max(pa.bbox_xyxy_norm[3], pb.bbox_xyxy_norm[3])

                        fight_events.append({
                            "camera_id": cam_id,
                            "event_type": "fight_detected",
                            "timestamp": now_iso,
                            "confidence": round(fight_conf, 3),
                            "bounding_box": {
                                "x":      round(merged_x1, 4),
                                "y":      round(merged_y1, 4),
                                "width":  round(merged_x2 - merged_x1, 4),
                                "height": round(merged_y2 - merged_y1, 4),
                            },
                        })
                        logger.info(
                            "[FightDetector] FIGHT on %s (conf=%.2f, criteria=%s, sustained=%d frames)",
                            cam_id, fight_conf, ["proximity"] + criteria_details, FIGHT_SUSTAIN_FRAMES,
                        )
                        break  # one fight event per frame is enough

        # Expire stale pair keys (people left the frame)
        stale = [k for k in history if k not in active_pairs]
        for k in stale:
            del history[k]

        # Update per-camera state for next frame
        self._prev_keypoints[cam_id] = [p.keypoints_norm for p in poses]
        self._prev_bboxes[cam_id] = [p.bbox_xyxy_norm for p in poses]
        self._prev_slots[cam_id] = slots

        return person_events + fight_events

    # ── Slot assignment for stable person tracking ─────────────────────

    def _assign_slots(self, cam_id: str, poses: list[_PersonPose]) -> list[int]:
        """Assign stable integer slot IDs to each person by IoU-matching to previous frame."""
        prev_bbs = self._prev_bboxes.get(cam_id, [])
        prev_slots = self._prev_slots.get(cam_id, [])

        if cam_id not in self._next_slot:
            self._next_slot[cam_id] = 0

        if not prev_bbs or not prev_slots:
            # First frame for this camera — assign fresh slots
            slots = []
            for _ in poses:
                slots.append(self._next_slot[cam_id])
                self._next_slot[cam_id] += 1
            return slots

        # Match each current person to previous person by best IoU
        used_prev = set()
        slots = [None] * len(poses)

        for i, pose in enumerate(poses):
            best_iou = 0.3  # minimum IoU to count as same person
            best_j = -1
            for j, prev_bb in enumerate(prev_bbs):
                if j in used_prev:
                    continue
                iou = _compute_iou_xyxy(pose.bbox_xyxy_norm, prev_bb)
                if iou > best_iou:
                    best_iou = iou
                    best_j = j

            if best_j >= 0:
                slots[i] = prev_slots[best_j]
                used_prev.add(best_j)

        # Assign new slots for unmatched people
        for i in range(len(slots)):
            if slots[i] is None:
                slots[i] = self._next_slot[cam_id]
                self._next_slot[cam_id] += 1

        return slots

    # ── Heuristic helpers ────────────────────────────────────────────────

    def _check_proximity(self, pa: _PersonPose, pb: _PersonPose) -> bool:
        dist = np.hypot(pa.center[0] - pb.center[0], pa.center[1] - pb.center[1])
        avg_diag = (pa.diagonal + pb.diagonal) / 2
        if avg_diag < 1e-6:
            return False
        return (dist / avg_diag) < FIGHT_PROXIMITY_RATIO

    def _check_arm_intrusion(self, pa: _PersonPose, pb: _PersonPose) -> bool:
        margin = FIGHT_ARM_INTRUSION_MARGIN
        for person, target in [(pa, pb), (pb, pa)]:
            tx1, ty1, tx2, ty2 = target.bbox_xyxy_norm
            tx1 -= margin
            ty1 -= margin
            tx2 += margin
            ty2 += margin
            for wi in _WRIST_INDICES:
                if person.keypoints_conf[wi] < FIGHT_KEYPOINT_CONFIDENCE_MIN:
                    continue
                wx, wy = person.keypoints_norm[wi]
                if tx1 <= wx <= tx2 and ty1 <= wy <= ty2:
                    return True
        return False

    def _check_aggressive_posture(self, person: _PersonPose) -> bool:
        for wrist_idx, shoulder_idx in _WRIST_SHOULDER_PAIRS:
            if (person.keypoints_conf[wrist_idx] < FIGHT_KEYPOINT_CONFIDENCE_MIN or
                    person.keypoints_conf[shoulder_idx] < FIGHT_KEYPOINT_CONFIDENCE_MIN):
                continue
            if person.keypoints_norm[wrist_idx, 1] < person.keypoints_norm[shoulder_idx, 1]:
                return True
        return False

    def _compute_velocities(self, cam_id: str, current_poses: list[_PersonPose]) -> list[float]:
        prev_kps = self._prev_keypoints.get(cam_id, [])
        prev_bbs = self._prev_bboxes.get(cam_id, [])

        if not prev_kps or not prev_bbs:
            return [0.0] * len(current_poses)

        velocities = []
        for pose in current_poses:
            best_iou = 0.0
            best_prev_kp = None
            for prev_bb, prev_kp in zip(prev_bbs, prev_kps):
                iou = _compute_iou_xyxy(pose.bbox_xyxy_norm, prev_bb)
                if iou > best_iou:
                    best_iou = iou
                    best_prev_kp = prev_kp

            if best_prev_kp is None or best_iou < 0.2:
                velocities.append(0.0)
                continue

            max_vel = 0.0
            for li in _LIMB_INDICES:
                if pose.keypoints_conf[li] < FIGHT_KEYPOINT_CONFIDENCE_MIN:
                    continue
                dx = pose.keypoints_norm[li, 0] - best_prev_kp[li, 0]
                dy = pose.keypoints_norm[li, 1] - best_prev_kp[li, 1]
                vel = np.hypot(dx, dy)
                if vel > max_vel:
                    max_vel = vel
            velocities.append(max_vel)

        return velocities


def _compute_iou_xyxy(box_a: tuple, box_b: tuple) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 1e-8 else 0.0
