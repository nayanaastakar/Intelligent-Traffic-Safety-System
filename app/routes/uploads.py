import os
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app
from app.config import Config
from app.models import db, DetectionSession
from app.utils.file_validation import allowed_file
from app.utils.storage import generate_unique_filename, get_rel_path
from app.detection.vehicle_detector import detect_vehicles_in_image
from app.detection.overspeed_detector import process_overspeed_image
from app.services.job_service import dispatch_video_job

bp = Blueprint("uploads", __name__, url_prefix="/uploads")

@bp.route("/")
def index():
    return render_template("uploads.html", active_page="uploads")

@bp.route("/process", methods=["POST"])
def process_upload():
    module = request.form.get("module", "vehicle")
    file = request.files.get("file")

    if not file or file.filename == "":
        return jsonify({"success": False, "error": "No file selected for upload"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Unsupported file format. Please upload MP4, AVI, MOV, JPG, or PNG."}), 400

    original_name = file.filename
    is_video = allowed_file(original_name, "video")
    media_type = "video" if is_video else "image"

    # Validate module vs filetype
    if not is_video and module in ["traffic", "accident"]:
        return jsonify({"success": False, "error": f"{module.capitalize()} requires a video file, not an image."}), 400

    unique_name = generate_unique_filename(original_name, f"proc_{module}")
    input_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
    file.save(input_path)

    session_id = uuid.uuid4().hex

    if not is_video:
        out_name = f"out_{session_id}.jpg"
        output_path = os.path.join(Config.OUTPUT_FOLDER, out_name)

        if module == "vehicle":
            res = detect_vehicles_in_image(input_path, output_path)
            session = DetectionSession(
                id=session_id,
                module=module,
                media_type="image",
                input_filename=original_name,
                input_path=get_rel_path(input_path),
                output_path=get_rel_path(output_path),
                evidence_path=get_rel_path(output_path),
                status="COMPLETED",
                total_vehicles=res["total_vehicles"]
            )
            session.set_summary(res)
            db.session.add(session)
            db.session.commit()
            return jsonify({
                "success": True,
                "is_video": False,
                "session_id": session_id,
                "result": {
                    "total_vehicles": res["total_vehicles"],
                    "output_image": f"/media/{get_rel_path(output_path)}"
                }
            })
        elif module == "overspeed":
            res = process_overspeed_image(input_path, speed_kmh=85, speed_limit_kmh=70, output_path=output_path)
            session = DetectionSession(
                id=session_id,
                module=module,
                media_type="image",
                input_filename=original_name,
                input_path=get_rel_path(input_path),
                output_path=get_rel_path(output_path),
                evidence_path=get_rel_path(output_path),
                status="COMPLETED",
                overspeed_count=1 if res["is_overspeed"] else 0
            )
            session.set_summary(res)
            db.session.add(session)
            db.session.commit()
            return jsonify({
                "success": True,
                "is_video": False,
                "session_id": session_id,
                "result": {
                    "is_overspeed": res["is_overspeed"],
                    "speed_kmh": res["speed_kmh"],
                    "output_image": f"/media/{get_rel_path(output_path)}"
                }
            })

    # Video background job
    out_name = f"out_{session_id}.mp4"
    output_path = os.path.join(Config.OUTPUT_FOLDER, out_name)

    session = DetectionSession(
        id=session_id,
        module=module,
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
        module=module,
        input_path=input_path,
        output_path=output_path,
        params={}
    )

    return jsonify({
        "success": True,
        "is_video": True,
        "session_id": session_id,
        "job_id": job_id,
        "message": f"Job queued for {module} processing"
    })
