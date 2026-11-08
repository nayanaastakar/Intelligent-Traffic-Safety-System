import os
import uuid
from werkzeug.utils import secure_filename
from app.config import Config

def init_storage():
    """Ensure all storage directories exist."""
    for folder in [Config.STORAGE_DIR, Config.UPLOAD_FOLDER, Config.OUTPUT_FOLDER, Config.EVIDENCE_FOLDER]:
        os.makedirs(folder, exist_ok=True)

def generate_unique_filename(original_filename, prefix=""):
    """Generate a unique collision-free filename preserving the extension."""
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
    uid = uuid.uuid4().hex[:10]
    safe_base = secure_filename(original_filename.rsplit(".", 1)[0]) if "." in original_filename else "file"
    if not safe_base:
        safe_base = "media"
    pfx = f"{prefix}_" if prefix else ""
    return f"{pfx}{safe_base}_{uid}.{ext}" if ext else f"{pfx}{safe_base}_{uid}"

def get_rel_path(abs_path, start=None):
    """Get relative path from storage directory for clean URL generation."""
    if not abs_path:
        return ""
    if not os.path.isabs(abs_path):
        return abs_path.replace("\\", "/")
    base = start or Config.BASE_DIR
    try:
        rel = os.path.relpath(abs_path, base)
        return rel.replace("\\", "/")
    except ValueError:
        return abs_path.replace("\\", "/")
