from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import db, DetectionSession, Alert

def get_dashboard_stats():
    """Aggregate real stats from persisted SQLite database."""
    total_vehicles = db.session.query(func.sum(DetectionSession.total_vehicles)).scalar() or 0
    total_sessions = DetectionSession.query.count()
    accidents_detected = db.session.query(func.sum(DetectionSession.accidents_count)).scalar() or 0
    overspeed_alerts = db.session.query(func.sum(DetectionSession.overspeed_count)).scalar() or 0
    drowsiness_alerts = db.session.query(func.sum(DetectionSession.drowsiness_count)).scalar() or 0
    total_videos = DetectionSession.query.filter_by(media_type="video").count()

    completed_sessions = DetectionSession.query.filter_by(status="COMPLETED").count()
    success_rate = round((completed_sessions / total_sessions * 100), 1) if total_sessions > 0 else 100.0

    # Density distribution
    density_counts = {
        "Low Density": DetectionSession.query.filter_by(density_level="Low Density").count(),
        "Medium Density": DetectionSession.query.filter_by(density_level="Medium Density").count(),
        "High Density": DetectionSession.query.filter_by(density_level="High Density").count(),
    }

    # Vehicle type distribution across sessions
    sessions = DetectionSession.query.filter(DetectionSession.summary_data.isnot(None)).all()
    aggregated_vehicles = {"car": 0, "truck": 0, "bus": 0, "motorbike": 0, "bicycle": 0}
    for s in sessions:
        summary = s.get_summary()
        v_dist = summary.get("vehicle_counts") or summary.get("vehicle_type_distribution") or {}
        for k, v in v_dist.items():
            if k in aggregated_vehicles:
                aggregated_vehicles[k] += int(v)
            else:
                aggregated_vehicles[k] = int(v)

    # Activity over last 7 days
    today = datetime.utcnow().date()
    days = [(today - timedelta(days=i)).strftime("%b %d") for i in range(6, -1, -1)]
    daily_activity = {day: 0 for day in days}
    all_sessions = DetectionSession.query.order_by(DetectionSession.created_at.desc()).limit(100).all()
    for s in all_sessions:
        if s.created_at:
            d_str = s.created_at.strftime("%b %d")
            if d_str in daily_activity:
                daily_activity[d_str] += 1

    # Module status and last processing times
    module_names = ["vehicle", "traffic", "accident", "overspeed", "drowsiness"]
    module_meta = {
        "vehicle": {"title": "Vehicle Detection", "desc": "YOLO Object Classification & Localization"},
        "traffic": {"title": "Traffic Density Analysis", "desc": "Volume Calculation & Congestion Classification"},
        "accident": {"title": "Accident Detection", "desc": "Proximity Collision & Delayed Confirmation"},
        "overspeed": {"title": "Overspeed Detection", "desc": "Radar Telemetry & Centroid Velocity Tracking"},
        "drowsiness": {"title": "Driver Drowsiness Detection", "desc": "MediaPipe Eye Aspect Ratio Facial Mesh"}
    }
    module_cards = []
    for m in module_names:
        last_s = DetectionSession.query.filter_by(module=m).order_by(DetectionSession.created_at.desc()).first()
        module_cards.append({
            "key": m,
            "title": module_meta[m]["title"],
            "desc": module_meta[m]["desc"],
            "status": "Available",
            "last_processed": last_s.created_at.strftime("%Y-%m-%d %H:%M") if (last_s and last_s.created_at) else "No runs yet",
            "total_runs": DetectionSession.query.filter_by(module=m).count()
        })

    # Recent sessions & latest alerts
    recent_sessions = [s.to_dict() for s in DetectionSession.query.order_by(DetectionSession.created_at.desc()).limit(6).all()]
    latest_alerts = [a.to_dict() for a in Alert.query.order_by(Alert.timestamp.desc()).limit(6).all()]

    return {
        "summary": {
            "total_vehicles": total_vehicles,
            "total_sessions": total_sessions,
            "accidents_detected": accidents_detected,
            "overspeed_alerts": overspeed_alerts,
            "drowsiness_alerts": drowsiness_alerts,
            "total_videos_processed": total_videos,
            "success_rate": success_rate
        },
        "vehicle_distribution": aggregated_vehicles,
        "density_distribution": density_counts,
        "daily_activity": daily_activity,
        "module_cards": module_cards,
        "recent_sessions": recent_sessions,
        "latest_alerts": latest_alerts
    }
