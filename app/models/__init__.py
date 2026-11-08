from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from app.models.session import DetectionSession, ProcessingJob
from app.models.alert import Alert
from app.models.settings import SystemSetting

__all__ = ["db", "DetectionSession", "ProcessingJob", "Alert", "SystemSetting"]
