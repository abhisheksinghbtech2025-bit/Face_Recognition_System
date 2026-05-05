import os

BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR     = os.path.join(BASE_DIR, "dataset", "faces")
LOGS_DIR        = os.path.join(BASE_DIR, "logs")
SNAPSHOTS_DIR   = os.path.join(BASE_DIR, "logs", "snapshots")
EXPORTS_DIR     = os.path.join(BASE_DIR, "exports")
ASSETS_DIR      = os.path.join(BASE_DIR, "assets")
ENCODINGS_FILE  = os.path.join(BASE_DIR, "dataset", "encodings.pkl")

DB_CONFIG = {
    "host"     : "localhost",
    "port"     : 3306,
    "user"     : "root",
    "password" : "Abhishek@21012007",   # ← change this
    "database" : "face_security_db",
}

APP_NAME    = "Face Security System"
APP_VERSION = "1.0.0"
THEME       = "dark"
COLOR_THEME = "blue"

DEFAULT_CAMERA_INDEX  = 0
CAMERA_WIDTH          = 640
CAMERA_HEIGHT         = 480
MAX_CAMERAS           = 4

RECOGNITION_TOLERANCE = 0.50
MIN_FACE_CONFIDENCE   = 0.60
UNKNOWN_LABEL         = "Unknown"

EAR_THRESHOLD         = 0.25
EAR_CONSEC_FRAMES     = 2
BLINKS_REQUIRED       = 2
LIVENESS_TIMEOUT_SEC  = 10

LOW_LIGHT_ENABLED     = True
GAMMA_VALUE           = 1.5

MAX_LOGIN_ATTEMPTS    = 5
SESSION_TIMEOUT_MIN   = 30
BCRYPT_ROUNDS         = 12

ALERT_SOUND_ENABLED    = True
ALERT_SNAPSHOT_ENABLED = True
ALERT_SOUND_FILE       = os.path.join(ASSETS_DIR, "alert.wav")

for _dir in [DATASET_DIR, LOGS_DIR, SNAPSHOTS_DIR, EXPORTS_DIR, ASSETS_DIR]:
    os.makedirs(_dir, exist_ok=True)