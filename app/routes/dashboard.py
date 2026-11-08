from flask import Blueprint, render_template
from app.services.stats_service import get_dashboard_stats

bp = Blueprint("dashboard", __name__)

@bp.route("/")
def index():
    stats = get_dashboard_stats()
    return render_template("dashboard.html", active_page="dashboard", stats=stats)
