import os
from flask import Blueprint, jsonify, request, send_from_directory, abort
from app.config import Config
from app.services.stats_service import get_dashboard_stats
from app.services.job_service import get_job_status
from app.services.alert_service import get_alerts, update_alert_status
from app.models import DetectionSession

bp = Blueprint("api", __name__, url_prefix="/api")

@bp.route("/dashboard/stats")
def dashboard_stats():
    return jsonify(get_dashboard_stats())

@bp.route("/modules/status")
def modules_status():
    stats = get_dashboard_stats()
    return jsonify(stats.get("module_cards", []))

@bp.route("/jobs/<string:job_id>")
def job_status(job_id):
    st = get_job_status(job_id)
    if st:
        return jsonify({"success": True, "job": st})
    return jsonify({"success": False, "error": "Job not found"}), 404

@bp.route("/jobs/<string:job_id>/result")
def job_result(job_id):
    st = get_job_status(job_id)
    if not st:
        return jsonify({"success": False, "error": "Job not found"}), 404
    session_id = st.get("session_id")
    session = DetectionSession.query.get(session_id)
    if session:
        return jsonify({"success": True, "session": session.to_dict()})
    return jsonify({"success": False, "error": "Session record missing"}), 404

@bp.route("/alerts")
def list_alerts():
    module = request.args.get("module")
    severity = request.args.get("severity")
    status = request.args.get("status")
    alerts = [a.to_dict() for a in get_alerts(module, severity, status)]
    return jsonify({"success": True, "alerts": alerts})

@bp.route("/alerts/<int:alert_id>", methods=["PATCH"])
def patch_alert(alert_id):
    data = request.get_json() or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"success": False, "error": "Status required"}), 400
    alert = update_alert_status(alert_id, new_status)
    if alert:
        return jsonify({"success": True, "alert": alert.to_dict()})
    return jsonify({"success": False, "error": "Alert not found"}), 404

@bp.route("/history")
def history_list():
    sessions = [s.to_dict() for s in DetectionSession.query.order_by(DetectionSession.created_at.desc()).limit(100).all()]
    return jsonify({"success": True, "sessions": sessions})

@bp.route("/analytics")
def analytics_data():
    return jsonify(get_dashboard_stats())
