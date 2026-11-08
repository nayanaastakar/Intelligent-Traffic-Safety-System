from flask import Blueprint, render_template, request, jsonify
from app.models import db, Alert
from app.services.alert_service import get_alerts, update_alert_status

bp = Blueprint("alerts", __name__, url_prefix="/alerts")

@bp.route("/")
def index():
    module = request.args.get("module", "all")
    severity = request.args.get("severity", "all")
    status = request.args.get("status", "all")
    
    alerts_list = get_alerts(module=module, severity=severity, status=status)
    
    total_alerts = Alert.query.count()
    active_alerts = Alert.query.filter_by(status="Active").count()
    critical_alerts = Alert.query.filter_by(severity="Critical").count()
    resolved_alerts = Alert.query.filter_by(status="Resolved").count()

    return render_template(
        "alerts.html",
        active_page="alerts",
        alerts=alerts_list,
        stats={
            "total": total_alerts,
            "active": active_alerts,
            "critical": critical_alerts,
            "resolved": resolved_alerts
        },
        current_filters={
            "module": module,
            "severity": severity,
            "status": status
        }
    )

@bp.route("/<int:alert_id>/status", methods=["POST"])
def change_status(alert_id):
    new_status = request.json.get("status") if request.is_json else request.form.get("status")
    if new_status not in ["Active", "Acknowledged", "Resolved"]:
        return jsonify({"success": False, "error": "Invalid status value"}), 400

    alert = update_alert_status(alert_id, new_status)
    if alert:
        return jsonify({"success": True, "alert": alert.to_dict()})
    return jsonify({"success": False, "error": "Alert not found"}), 404
