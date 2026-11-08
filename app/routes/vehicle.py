import os
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app
from app.config import Config
from app.models import db, DetectionSession
from app.utils.file_validation import allowed_file
from app.utils.storage import generate_unique_filename, get_rel_path
from app.detection.vehicle_detector import detect_vehicles_in_image
from app.services.job_service import dispatch_video_job

bp = Blueprint("vehicle", __name__, url_prefix="/vehicle")

@bp.route("/")
def index():
    return render_template("vehicle.html", active_page="vehicle")

@bp.route("/detect", methods=["POST"])
def detect():
    source_type = request.form.get("source_type", "sample") # sample or upload
    conf_thresh = float(request.form.get("conf_threshold", 0.25))
    
    input_path = None
    original_name = None
    media_type = "image"

    if source_type == "sample":
        sample_choice = request.form.get("sample_file", "real_traffic_intersection.jpg")
        if sample_choice in ["video1.mp4", "sample_traffic.mp4"]:
            input_path = os.path.join(Config.BASE_DIR, "sample_videos", "video1.mp4")
            if not os.path.exists(input_path):
                input_path = os.path.join(Config.SAMPLE_DATA_FOLDER, "sample_traffic.mp4")
            original_name = "video1.mp4"
            media_type = "video"
        elif sample_choice in ["real_highway_car.jpg", "sample_car.png"]:
            input_path = os.path.join(Config.SAMPLE_DATA_FOLDER, "real_highway_car.jpg")
            if not os.path.exists(input_path):
                input_path = os.path.join(Config.SAMPLE_DATA_FOLDER, "sample_car.png")
            original_name = "real_highway_car.jpg"
            media_type = "image"
        else:
            input_path = os.path.join(Config.SAMPLE_DATA_FOLDER, "real_traffic_intersection.jpg")
            if not os.path.exists(input_path):
                input_path = os.path.join(Config.SAMPLE_DATA_FOLDER, "sample_highway.png")
            original_name = "real_traffic_intersection.jpg"
            media_type = "image"
    else:
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "No file uploaded"}), 400
        if not allowed_file(file.filename):
            return jsonify({"success": False, "error": "Unsupported file format"}), 400
        
        original_name = file.filename
        unique_name = generate_unique_filename(original_name, "veh")
        input_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
        file.save(input_path)
        media_type = "video" if allowed_file(original_name, "video") else "image"

    session_id = uuid.uuid4().hex

    if media_type == "image":
        out_name = f"out_{session_id}.jpg"
        output_path = os.path.join(Config.OUTPUT_FOLDER, out_name)
        
        try:
            res = detect_vehicles_in_image(input_path, output_path, conf_threshold=conf_thresh)
            
            session = DetectionSession(
                id=session_id,
                module="vehicle",
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
                    "vehicle_counts": res["vehicle_counts"],
                    "detected_items": res["detected_items"],
                    "output_image": f"/media/{get_rel_path(output_path)}"
                }
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    else:
        out_name = f"out_{session_id}.mp4"
        output_path = os.path.join(Config.OUTPUT_FOLDER, out_name)

        session = DetectionSession(
            id=session_id,
            module="vehicle",
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
            module="vehicle",
            input_path=input_path,
            output_path=output_path,
            params={"conf_threshold": conf_thresh}
        )

        return jsonify({
            "success": True,
            "is_video": True,
            "session_id": session_id,
            "job_id": job_id,
            "message": "Video vehicle detection started"
        })
