from pydantic import BaseModel
from typing import Literal


class BoundingBox(BaseModel):
    x: float       # normalized 0.0-1.0
    y: float
    width: float
    height: float


class DetectionEvent(BaseModel):
    camera_id: str
    event_type: str
    timestamp: str  # ISO-8601
    confidence: float
    bounding_box: BoundingBox


class CameraStatus(BaseModel):
    id: str
    name: str
    location: str
    status: Literal["online", "offline"]
    stream_url: str
