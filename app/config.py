import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get("SECRET_KEY", "traffic-safety-secret-key-2026")
    
    # Storage paths
    STORAGE_DIR = os.path.join(BASE_DIR, "storage")
    UPLOAD_FOLDER = os.path.join(STORAGE_DIR, "uploads")
    OUTPUT_FOLDER = os.path.join(STORAGE_DIR, "outputs")
    EVIDENCE_FOLDER = os.path.join(STORAGE_DIR, "evidence")
    SAMPLE_DATA_FOLDER = os.path.join(BASE_DIR, "data")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(STORAGE_DIR, 'traffic_safety.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload limits (Default: 200MB)
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "mp4", "avi", "mov", "mkv", "webm"}
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}
    
    # YOLO assets
    YOLO_CFG = os.path.join(BASE_DIR, "yolov3-tiny.cfg")
    YOLO_WEIGHTS = os.path.join(BASE_DIR, "yolov3-tiny.weights")
    YOLO_FULL_CFG = os.path.join(BASE_DIR, "yolov3.cfg")
    YOLO_FULL_WEIGHTS = os.path.join(BASE_DIR, "yolov3.weights")
    COCO_NAMES = os.path.join(BASE_DIR, "coco.names")
