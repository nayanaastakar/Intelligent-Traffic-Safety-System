import os
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app
from app.config import Config
from app.models import db, DetectionSession
from app.utils.file_validation import allowed_file
from app.utils.storage import generate_unique_filename, get_rel_path
from app.detection.overspeed_detector import process_overspeed_image
from app.services.job_service import dispatch_video_job

bp = Blueprint("overspeed", __name__, url_prefix="/overspeed")

@bp.route("/")
def index():
    return render_template("overspeed.html", active_page="overspeed")

@bp.route("/detect", methods=["POST"])
def detect():
    mode = request.form.get("mode", "image") # image or video
    speed_limit = float(request.form.get("speed_limit", 70))
    source_type = request.form.get("source_type", "sample")

    session_id = uuid.uuid4().hex

    if mode == "image":
        simulated_speed = float(request.form.get("simulated_speed", 85))
        input_path = None
        original_name = None

        if source_type == "sample":
            input_path = os.path.join(Config.SAMPLE_DATA_FOLDER, "sample_car.png")
            original_name = "sample_car.png"
        else:
            file = request.files.get("file")
            if not file or file.filename == "":
                return jsonify({"success": False, "error": "No image uploaded"}), 400
            if not allowed_file(file.filename, "image"):
                return jsonify({"success": False, "error": "File must be an image (png, jpg, jpeg)"}), 400
            
            original_name = file.filename
            unique_name = generate_unique_filename(original_name, "speed")
            input_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
            file.save(input_path)

        out_name = f"out_{session_id}.jpg"
        output_path = os.path.join(Config.OUTPUT_FOLDER, out_name)

        try:
            res = process_overspeed_image(
                image_path=input_path,
                speed_kmh=simulated_speed,
                speed_limit_kmh=speed_limit,
                output_path=output_path
            )

            session = DetectionSession(
                id=session_id,
                module="overspeed",
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
                    "speed_limit_kmh": res["speed_limit_kmh"],
                    "excess_kmh": res["excess_kmh"],
                    "status": res["status"],
                    "output_image": f"/media/{get_rel_path(output_path)}"
                }
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    else: # Video tracking mode
        input_path = None
        original_name = None

        if source_type == "sample":
            input_path = os.path.join(Config.SAMPLE_DATA_FOLDER, "sample_traffic.mp4")
            original_name = "sample_traffic.mp4"
        else:
            file = request.files.get("file")
            if not file or file.filename == "":
                return jsonify({"success": False, "error": "No video uploaded"}), 400
            if not allowed_file(file.filename, "video"):
                return jsonify({"success": False, "error": "File must be a video"}), 400
            
            original_name = file.filename
            unique_name = generate_unique_filename(original_name, "speed_vid")
            input_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
            file.save(input_path)

        out_name = f"out_{session_id}.mp4"
        output_path = os.path.join(Config.OUTPUT_FOLDER, out_name)

        session = DetectionSession(
            id=session_id,
            module="overspeed",
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
            module="overspeed",
            input_path=input_path,
            output_path=output_path,
            params={"speed_limit_kmh": speed_limit}
        )

        return jsonify({
            "success": True,
            "is_video": True,
            "session_id": session_id,
            "job_id": job_id,
            "message": "Video speed tracking job dispatched"
        })
