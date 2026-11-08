from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app.models import db, SystemSetting

bp = Blueprint("settings", __name__, url_prefix="/settings")

@bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        settings_dict = {
            "yolo_conf_threshold": float(request.form.get("yolo_conf_threshold", 0.40)),
            "yolo_nms_threshold": float(request.form.get("yolo_nms_threshold", 0.40)),
            "proximity_threshold": float(request.form.get("proximity_threshold", 0.50)),
            "speed_limit_kmh": int(request.form.get("speed_limit_kmh", 70)),
            "speed_calibration_factor": float(request.form.get("speed_calibration_factor", 1.25)),
            "ear_threshold": float(request.form.get("ear_threshold", 0.23)),
            "consecutive_drowsy_frames": int(request.form.get("consecutive_drowsy_frames", 15)),
            "audio_alerts_enabled": "audio_alerts_enabled" in request.form,
            "camera_index": int(request.form.get("camera_index", 0)),
            "max_upload_size_mb": int(request.form.get("max_upload_size_mb", 200)),
            "theme_mode": request.form.get("theme_mode", "dark")
        }

        for key, val in settings_dict.items():
            SystemSetting.set(key, val)

        flash("System settings successfully updated and saved.", "success")
        return redirect(url_for("settings.index"))

    current_settings = SystemSetting.get_all()
    return render_template("settings.html", active_page="settings", settings=current_settings)
