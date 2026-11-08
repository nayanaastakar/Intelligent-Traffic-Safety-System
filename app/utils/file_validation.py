import os
from app.config import Config

def allowed_file(filename, file_type="any"):
    """
    Validate file extension against allowed whitelist.
    file_type: 'any', 'image', 'video'
    """
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    if file_type == "image":
        return ext in Config.ALLOWED_IMAGE_EXTENSIONS
    elif file_type == "video":
        return ext in Config.ALLOWED_VIDEO_EXTENSIONS
    return ext in Config.ALLOWED_EXTENSIONS

def validate_file_size(file_obj, max_mb=200):
    """Check file size before heavy processing."""
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(0)
    return size <= (max_mb * 1024 * 1024), size
