import io
import csv
from app.models import DetectionSession, Alert

def generate_sessions_csv():
    """Export detection sessions to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Session ID", "Module", "Media Type", "Input File",
        "Status", "Vehicles Counted", "Density Level",
        "Accidents", "Overspeed", "Drowsiness",
        "Duration (s)", "Created At"
    ])
    sessions = DetectionSession.query.order_by(DetectionSession.created_at.desc()).all()
    for s in sessions:
        writer.writerow([
            s.id, s.module, s.media_type, s.input_filename,
            s.status, s.total_vehicles, s.density_level or "N/A",
            s.accidents_count, s.overspeed_count, s.drowsiness_count,
            round(s.duration_sec, 2), s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else ""
        ])
    return output.getvalue()

def generate_alerts_csv():
    """Export alerts to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Alert ID", "Type", "Severity", "Module",
        "Description", "Status", "Timestamp"
    ])
    alerts = Alert.query.order_by(Alert.timestamp.desc()).all()
    for a in alerts:
        writer.writerow([
            a.id, a.alert_type, a.severity, a.module,
            a.description, a.status, a.timestamp.strftime("%Y-%m-%d %H:%M:%S") if a.timestamp else ""
        ])
    return output.getvalue()
