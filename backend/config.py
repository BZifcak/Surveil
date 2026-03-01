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
MOTION_MIN_AREA = 200  # px² — contours smaller than this are noise

# --- Demo toggles ---
# Flip any of these and uvicorn --reload picks it up in ~1 second
ENABLE_PERSON_DETECTION = True
ENABLE_MOTION_DETECTION = True
ENABLE_WEAPON_DETECTION = True  # uses local weapon.pt if present, else falls back to Gemini (requires GEMINI_API_KEY)
ENABLE_FIGHT_DETECTION = True

# --- Fight detection thresholds ---
FIGHT_POSE_CONFIDENCE_THRESHOLD = 0.25
FIGHT_KEYPOINT_CONFIDENCE_MIN = 0.3
FIGHT_PROXIMITY_RATIO = 0.8          # max center-dist / avg-bbox-diagonal (tighter = must be very close)
FIGHT_ARM_INTRUSION_MARGIN = 0.02    # normalized margin for wrist-in-box check
FIGHT_VELOCITY_THRESHOLD = 0.12      # normalized keypoint displacement/frame (higher = only fast swings)
FIGHT_MIN_CRITERIA = 2               # of 3 non-proximity heuristics must fire (proximity is mandatory)
FIGHT_SUSTAIN_FRAMES = 3             # criteria must hold for N consecutive frames to trigger
FIGHT_EVENT_COOLDOWN_SECS = 3.0      # min seconds between fight events per cam

# CORS
ALLOWED_ORIGINS = ["*"]
