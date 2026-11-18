
from pathlib import Path

# Project directories
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"

# AI model paths
FACE_DETECTION_MODEL = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
FACE_RECOGNITION_MODEL = MODEL_DIR / "face_recognition_sface_2021dec.onnx"

# Camera settings
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Face detection settings
DETECTION_SCORE_THRESHOLD = 0.7
NMS_THRESHOLD = 0.3
TOP_K = 5000

# Face recognition setting
# This is an initial value, not a validated security threshold.
FACE_MATCH_THRESHOLD = 0.363

# Evidence settings
EVIDENCE_DIR = BASE_DIR / "evidence"
UNKNOWN_EVIDENCE_DIR = EVIDENCE_DIR / "unknown"
RECOGNIZED_EVIDENCE_DIR = EVIDENCE_DIR / "recognized"

for folder in [
    UNKNOWN_EVIDENCE_DIR,
    RECOGNIZED_EVIDENCE_DIR
]:
    folder.mkdir(parents=True, exist_ok=True)


AUTHORIZED_DIR = BASE_DIR / "enrollment" / "authorized"
AUTHORIZED_DIR.mkdir(parents=True, exist_ok=True)  


# Unknown person monitoring
UNKNOWN_CAPTURE_SECONDS = 10
UNKNOWN_ALERT_SECONDS = 30

# Tracking settings
TRACK_IOU_THRESHOLD = 0.30
TRACK_MAX_MISSING_SECONDS = 1.5
