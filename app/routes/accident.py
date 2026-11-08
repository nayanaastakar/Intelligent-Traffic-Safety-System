import os
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app
from app.config import Config
from app.models import db, DetectionSession
from app.utils.file_validation import allowed_file
from app.utils.storage import generate_unique_filename, get_rel_path
from app.services.job_service import dispatch_video_job

bp = Blueprint("accident", __name__, url_prefix="/accident")

@bp.route("/")
def index():
    return render_template("accident.html", active_page="accident")

@bp.route("/detect", methods=["POST"])
def detect():
    source_type = request.form.get("source_type", "sample")
    proximity = float(request.form.get("proximity_threshold", 0.5))
    conf_thresh = float(request.form.get("conf_threshold", 0.4))

    input_path = None
    original_name = None

    if source_type == "sample":
        input_path = os.path.join(Config.SAMPLE_DATA_FOLDER, "sample_traffic.mp4")
        original_name = "sample_traffic.mp4"
    else:
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "No accident video uploaded"}), 400
        if not allowed_file(file.filename, "video"):
            return jsonify({"success": False, "error": "Unsupported video format"}), 400
        
        original_name = file.filename
        unique_name = generate_unique_filename(original_name, "accident")
        input_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
        file.save(input_path)

    session_id = uuid.uuid4().hex
    out_name = f"out_{session_id}.mp4"
    output_path = os.path.join(Config.OUTPUT_FOLDER, out_name)

    session = DetectionSession(
        id=session_id,
        module="accident",
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
        module="accident",
        input_path=input_path,
        output_path=output_path,
        params={"proximity_threshold": proximity, "conf_threshold": conf_thresh}
    )

    return jsonify({
        "success": True,
        "session_id": session_id,
        "job_id": job_id,
        "message": "Accident detection pipeline dispatched"
    })
