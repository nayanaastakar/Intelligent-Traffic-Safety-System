import os
import uuid
from flask import Blueprint, render_template, request, jsonify, Response, current_app
from app.config import Config
from app.models import db, DetectionSession
from app.utils.file_validation import allowed_file
from app.utils.storage import generate_unique_filename, get_rel_path
from app.detection.drowsiness_detector import (
    CameraStreamController,
    generate_drowsiness_stream
)
from app.services.job_service import dispatch_video_job

bp = Blueprint("drowsiness", __name__, url_prefix="/drowsiness")

@bp.route("/")
def index():
    return render_template("drowsiness.html", active_page="drowsiness")

@bp.route("/start_camera", methods=["POST"])
def start_camera():
    camera_idx = int(request.form.get("camera_index", 0))
    ear_thresh = float(request.form.get("ear_threshold", 0.23))
    consec_req = int(request.form.get("consecutive_frames", 15))

    controller = CameraStreamController.get_instance()
    try:
        controller.start(camera_index=camera_idx, ear_threshold=ear_thresh, consecutive_required=consec_req)
        return jsonify({"success": True, "message": "Camera stream started"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@bp.route("/stop_camera", methods=["POST"])
def stop_camera():
    controller = CameraStreamController.get_instance()
    controller.stop()
    return jsonify({"success": True, "message": "Camera stream stopped"})

@bp.route("/stream")
def stream():
    controller = CameraStreamController.get_instance()
    if not controller.is_running:
        return "Camera is not active", 404
    return Response(generate_drowsiness_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

@bp.route("/status")
def status():
    controller = CameraStreamController.get_instance()
    return jsonify({
        "is_running": controller.is_running,
        "ear": controller.latest_ear,
        "status": controller.latest_status,
        "alerts_count": controller.alerts_count
    })

@bp.route("/process_video", methods=["POST"])
def process_video():
    source_type = request.form.get("source_type", "sample")
    ear_thresh = float(request.form.get("ear_threshold", 0.23))
    consec_req = int(request.form.get("consecutive_frames", 15))

    input_path = None
    original_name = None

    if source_type == "sample":
        input_path = os.path.join(Config.BASE_DIR, "sample_videos", "video5.mp4")
        if not os.path.exists(input_path):
            input_path = os.path.join(Config.SAMPLE_DATA_FOLDER, "sample_traffic.mp4")
        original_name = "video5.mp4"
    else:
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "No video uploaded"}), 400
        if not allowed_file(file.filename, "video"):
            return jsonify({"success": False, "error": "File must be a video"}), 400

        original_name = file.filename
        unique_name = generate_unique_filename(original_name, "drowsy")
        input_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
        file.save(input_path)

    session_id = uuid.uuid4().hex
    out_name = f"out_{session_id}.mp4"
    output_path = os.path.join(Config.OUTPUT_FOLDER, out_name)

    session = DetectionSession(
        id=session_id,
        module="drowsiness",
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
        module="drowsiness",
        input_path=input_path,
        output_path=output_path,
        params={"ear_threshold": ear_thresh, "consecutive_frames_req": consec_req}
    )

    return jsonify({
        "success": True,
        "session_id": session_id,
        "job_id": job_id,
        "message": "Drowsiness video analysis dispatched"
    })
