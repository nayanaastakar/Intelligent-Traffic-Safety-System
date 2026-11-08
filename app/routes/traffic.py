import os
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app
from app.config import Config
from app.models import db, DetectionSession
from app.utils.file_validation import allowed_file
from app.utils.storage import generate_unique_filename, get_rel_path
from app.services.job_service import dispatch_video_job

bp = Blueprint("traffic", __name__, url_prefix="/traffic")

@bp.route("/")
def index():
    return render_template("traffic.html", active_page="traffic")

@bp.route("/analyze", methods=["POST"])
def analyze():
    source_type = request.form.get("source_type", "sample")
    conf_thresh = float(request.form.get("conf_threshold", 0.25))
    
    input_path = None
    original_name = None

    if source_type == "sample":
        sample_choice = request.form.get("sample_file", "video1.mp4")
        input_path = os.path.join(Config.BASE_DIR, "sample_videos", "video1.mp4")
        if not os.path.exists(input_path):
            input_path = os.path.join(Config.SAMPLE_DATA_FOLDER, "sample_traffic.mp4")
        original_name = "video1.mp4"
    else:
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "No video file uploaded"}), 400
        if not allowed_file(file.filename, "video"):
            return jsonify({"success": False, "error": "Unsupported video format (must be mp4/avi/mov/webm)"}), 400
        
        original_name = file.filename
        unique_name = generate_unique_filename(original_name, "traffic")
        input_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
        file.save(input_path)

    session_id = uuid.uuid4().hex
    out_name = f"out_{session_id}.mp4"
    output_path = os.path.join(Config.OUTPUT_FOLDER, out_name)

    session = DetectionSession(
        id=session_id,
        module="traffic",
        media_type="video",
        input_filename=original_name,
        input_path=get_rel_path(input_path),
        status="QUEUED"
    )
    db.session.add(session)
    db.session.commit()

    job_id = dispatch_video_job(
        current_app._get_current_object(),
        session_id=session_id,
        module="traffic",
        input_path=input_path,
        output_path=output_path,
        params={"conf_threshold": conf_thresh}
    )

    return jsonify({
        "success": True,
        "session_id": session_id,
        "job_id": job_id,
        "message": "Traffic density analysis initiated"
    })
