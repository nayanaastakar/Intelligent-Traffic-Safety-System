from flask import Blueprint, render_template, Response
from app.services.stats_service import get_dashboard_stats
from app.services.report_service import generate_sessions_csv, generate_alerts_csv

bp = Blueprint("analytics", __name__, url_prefix="/analytics")

@bp.route("/")
def index():
    stats = get_dashboard_stats()
    return render_template("analytics.html", active_page="analytics", stats=stats)

@bp.route("/export/sessions.csv")
def export_sessions():
    csv_data = generate_sessions_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=traffic_sessions_report.csv"}
    )

@bp.route("/export/alerts.csv")
def export_alerts():
    csv_data = generate_alerts_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=traffic_alerts_report.csv"}
    )
