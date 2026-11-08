from datetime import datetime
import json
from app.models import db

class DetectionSession(db.Model):
    __tablename__ = "detection_sessions"

    id = db.Column(db.String(36), primary_key=True)
    module = db.Column(db.String(50), nullable=False) # vehicle, traffic, accident, overspeed, drowsiness
    media_type = db.Column(db.String(20), default="video") # video, image, stream
    input_filename = db.Column(db.String(255), nullable=True)
    input_path = db.Column(db.String(500), nullable=True)
    output_path = db.Column(db.String(500), nullable=True)
    evidence_path = db.Column(db.String(500), nullable=True)
    
    status = db.Column(db.String(30), default="QUEUED") # QUEUED, PROCESSING, COMPLETED, FAILED, CANCELLED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    duration_sec = db.Column(db.Float, default=0.0)
    
    # Specific metrics
    total_vehicles = db.Column(db.Integer, default=0)
    density_level = db.Column(db.String(30), nullable=True) # Low, Medium, High
    accidents_count = db.Column(db.Integer, default=0)
    overspeed_count = db.Column(db.Integer, default=0)
    drowsiness_count = db.Column(db.Integer, default=0)
    
    summary_data = db.Column(db.Text, default="{}") # JSON-serialized details
    error_message = db.Column(db.Text, nullable=True)
    
    # Relationships
    alerts = db.relationship("Alert", backref="session", lazy="dynamic", cascade="all, delete-orphan")

    def get_summary(self):
        try:
            return json.loads(self.summary_data or "{}")
        except Exception:
            return {}

    def set_summary(self, data):
        self.summary_data = json.dumps(data)

    def to_dict(self):
        return {
            "id": self.id,
            "module": self.module,
            "media_type": self.media_type,
            "input_filename": self.input_filename,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "evidence_path": self.evidence_path,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "completed_at": self.completed_at.strftime("%Y-%m-%d %H:%M:%S") if self.completed_at else None,
            "duration_sec": round(self.duration_sec, 2) if self.duration_sec else 0.0,
            "total_vehicles": self.total_vehicles,
            "density_level": self.density_level,
            "accidents_count": self.accidents_count,
            "overspeed_count": self.overspeed_count,
            "drowsiness_count": self.drowsiness_count,
            "summary": self.get_summary(),
            "error_message": self.error_message,
        }


class ProcessingJob(db.Model):
    __tablename__ = "processing_jobs"

    id = db.Column(db.String(36), primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("detection_sessions.id"), nullable=True)
    progress_percent = db.Column(db.Integer, default=0)
    current_frame = db.Column(db.Integer, default=0)
    total_frames = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default="QUEUED")
    message = db.Column(db.String(255), default="Job initialized")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "progress_percent": self.progress_percent,
            "current_frame": self.current_frame,
            "total_frames": self.total_frames,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
