from pathlib import Path

BASE_DIR = Path(__file__).parent
VIDEOS_DIR = BASE_DIR / "videos"
MODEL_DIR = BASE_DIR / "models"

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
        "Courtyard",
        "Side Entrance",
        "Gymnasium",
    ])
]

# MJPEG streaming
MJPEG_FPS_TARGET = 15
JPEG_QUALITY = 80

# Detection pipeline
DETECTION_FPS = 1
DETECTION_DEVICE = "mps"  # "cpu" | "mps" (Apple Silicon) | "cuda" (NVIDIA GPU)
PERSON_CONFIDENCE_THRESHOLD = 0.25
WEAPON_CONFIDENCE_THRESHOLD = 0.50
GEMINI_WEAPON_COOLDOWN_SECS = 30  # seconds between Gemini calls per camera (only fires when a person is detected — free tier is 2 RPM)
MOTION_MIN_AREA = 200  # px² — contours smaller than this are noise

# --- Demo toggles ---
# Flip any of these and uvicorn --reload picks it up in ~1 second
ENABLE_PERSON_DETECTION = True
ENABLE_MOTION_DETECTION = True
ENABLE_WEAPON_DETECTION = False  # uses local weapon.pt if present, else falls back to Gemini (requires GEMINI_API_KEY)

# CORS
ALLOWED_ORIGINS = ["*"]
