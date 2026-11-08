import json
from app.models import db

DEFAULT_SETTINGS = {
    "yolo_conf_threshold": 0.40,
    "yolo_nms_threshold": 0.40,
    "proximity_threshold": 0.50,
    "speed_limit_kmh": 70,
    "speed_calibration_factor": 1.25,
    "ear_threshold": 0.23,
    "consecutive_drowsy_frames": 15,
    "audio_alerts_enabled": True,
    "camera_index": 0,
    "max_upload_size_mb": 200,
    "theme_mode": "dark"
}

class SystemSetting(db.Model):
    __tablename__ = "system_settings"

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=False)

    @classmethod
    def get(cls, key, default=None):
        record = cls.query.filter_by(key=key).first()
        if record:
            try:
                return json.loads(record.value)
            except Exception:
                return record.value
        return default if default is not None else DEFAULT_SETTINGS.get(key)

    @classmethod
    def set(cls, key, val):
        record = cls.query.filter_by(key=key).first()
        val_str = json.dumps(val)
        if record:
            record.value = val_str
        else:
            record = cls(key=key, value=val_str)
            db.session.add(record)
        db.session.commit()

    @classmethod
    def get_all(cls):
        all_records = {r.key: json.loads(r.value) for r in cls.query.all()}
        # Merge with defaults
        merged = DEFAULT_SETTINGS.copy()
        merged.update(all_records)
        return merged
