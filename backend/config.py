from pathlib import Path

BASE_DIR = Path(__file__).parent
VIDEOS_DIR = BASE_DIR / "videos"

CAMERAS = [
    {"id": f"cam_{i}", "name": f"Camera {i}", "location": label}
    for i, label in enumerate([
        "Main Entrance",
        "Lobby",
        "Parking Lot A",
        "Parking Lot B",
        "Stairwell North",
        "Stairwell South",
        "Server Room",
        "Loading Dock",
        "Rooftop",
    ])
]

# MJPEG streaming
MJPEG_FPS_TARGET = 15
JPEG_QUALITY = 80

# Mock detector
DETECTION_INTERVAL_MIN = 3.0
DETECTION_INTERVAL_MAX = 8.0
DETECTION_TYPES = [
    "person_detected",
    "fight",
    "fire_smoke",
    "weapon_detected",
    "person_falling",
]
CONFIDENCE_MIN = 0.70
CONFIDENCE_MAX = 1.00

# CORS
ALLOWED_ORIGINS = ["*"]
