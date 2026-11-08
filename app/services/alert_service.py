from datetime import datetime
from app.models import db, Alert

def create_alert(alert_type, severity, module, description, evidence_image=None, session_id=None):
    """Create and persist an alert record."""
    alert = Alert(
        session_id=session_id,
        alert_type=alert_type,
        severity=severity,
        module=module,
        description=description,
        evidence_image=evidence_image,
        timestamp=datetime.utcnow(),
        status="Active"
    )
    db.session.add(alert)
    db.session.commit()
    return alert

def get_alerts(module=None, severity=None, status=None, limit=100):
    query = Alert.query
    if module and module != "all":
        query = query.filter_by(module=module)
    if severity and severity != "all":
        query = query.filter_by(severity=severity)
    if status and status != "all":
        query = query.filter_by(status=status)
    return query.order_by(Alert.timestamp.desc()).limit(limit).all()

def update_alert_status(alert_id, new_status):
    alert = Alert.query.get(alert_id)
    if alert:
        alert.status = new_status
        db.session.commit()
        return alert
    return None
