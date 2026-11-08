from flask import Blueprint, render_template, request, jsonify
from app.models import db, DetectionSession

bp = Blueprint("history", __name__, url_prefix="/history")

@bp.route("/")
def index():
    module = request.args.get("module", "all")
    status = request.args.get("status", "all")
    search = request.args.get("search", "").strip()

    query = DetectionSession.query
    if module and module != "all":
        query = query.filter_by(module=module)
    if status and status != "all":
        query = query.filter_by(status=status)
    if search:
        query = query.filter(DetectionSession.input_filename.ilike(f"%{search}%"))

    sessions = query.order_by(DetectionSession.created_at.desc()).all()

    return render_template(
        "history.html",
        active_page="history",
        sessions=sessions,
        current_filters={"module": module, "status": status, "search": search}
    )

@bp.route("/<string:session_id>/delete", methods=["POST", "DELETE"])
def delete_session(session_id):
    session = DetectionSession.query.get(session_id)
    if not session:
        return jsonify({"success": False, "error": "Session record not found"}), 404

    try:
        db.session.delete(session)
        db.session.commit()
        return jsonify({"success": True, "message": "Record removed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
