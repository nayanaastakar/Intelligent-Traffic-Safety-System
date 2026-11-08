from datetime import datetime
from app.models import db

class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(36), db.ForeignKey("detection_sessions.id"), nullable=True)
    alert_type = db.Column(db.String(50), nullable=False) # Accident Alert, Overspeed Warning, Drowsiness Alert, Traffic Congestion, System Warning
    severity = db.Column(db.String(20), default="Medium") # Critical, High, Medium, Low, Informational
    module = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    evidence_image = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Active") # Active, Acknowledged, Resolved

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "module": self.module,
            "description": self.description,
            "evidence_image": self.evidence_image,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None,
            "status": self.status,
        }
