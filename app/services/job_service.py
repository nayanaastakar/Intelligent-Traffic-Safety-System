import time
import uuid
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from app.models import db, DetectionSession, ProcessingJob
from app.services.alert_service import create_alert
from app.utils.storage import get_rel_path
from app.detection.vehicle_detector import detect_vehicles_in_video
from app.detection.traffic_detector import analyze_traffic_density
from app.detection.accident_detector import detect_accidents_in_video
from app.detection.overspeed_detector import process_overspeed_video
from app.detection.drowsiness_detector import process_drowsiness_video

executor = ThreadPoolExecutor(max_workers=3)

# In-memory fast status lookup
JOB_STATUS_CACHE = {}

def get_job_status(job_id):
    if job_id in JOB_STATUS_CACHE:
        return JOB_STATUS_CACHE[job_id]
    job = ProcessingJob.query.get(job_id)
    if job:
        return job.to_dict()
    return None

def update_job_progress(job_id, current_frame, total_frames):
    percent = int((current_frame / total_frames) * 100) if total_frames > 0 else 0
    percent = min(100, max(0, percent))
    if job_id in JOB_STATUS_CACHE:
        JOB_STATUS_CACHE[job_id]["progress_percent"] = percent
        JOB_STATUS_CACHE[job_id]["current_frame"] = current_frame
        JOB_STATUS_CACHE[job_id]["total_frames"] = total_frames
        JOB_STATUS_CACHE[job_id]["message"] = f"Processing frame {current_frame} of {total_frames} ({percent}%)"

def run_background_job(app, job_id, session_id, module, input_path, output_path, params):
    with app.app_context():
        start_time = time.time()
        job = ProcessingJob.query.get(job_id)
        session = DetectionSession.query.get(session_id)
        if not job or not session:
            return

        job.status = "PROCESSING"
        job.message = f"Executing {module} pipeline..."
        session.status = "PROCESSING"
        db.session.commit()

        JOB_STATUS_CACHE[job_id]["status"] = "PROCESSING"
        JOB_STATUS_CACHE[job_id]["message"] = "Processing video frames..."

        def progress_cb(cur, tot):
            update_job_progress(job_id, cur, tot)

        try:
            summary = {}
            if module == "vehicle":
                summary = detect_vehicles_in_video(
                    input_path, output_path, progress_callback=progress_cb,
                    conf_threshold=params.get("conf_threshold", 0.4)
                )
                session.total_vehicles = summary.get("total_detections", 0)

            elif module == "traffic":
                summary = analyze_traffic_density(
                    input_path, output_path, progress_callback=progress_cb,
                    conf_threshold=params.get("conf_threshold", 0.4)
                )
                session.total_vehicles = summary.get("total_vehicles_counted", 0)
                session.density_level = summary.get("density_classification")
                if summary.get("congestion_alert"):
                    create_alert(
                        alert_type="Traffic Congestion",
                        severity="High",
                        module="traffic",
                        description=f"Heavy traffic congestion detected (Average: {summary.get('average_density')} vehicles/frame)",
                        evidence_image=get_rel_path(summary.get("evidence_path")),
                        session_id=session_id
                    )

            elif module == "accident":
                summary = detect_accidents_in_video(
                    input_path, output_path, progress_callback=progress_cb,
                    proximity_factor=params.get("proximity_threshold", 0.5),
                    conf_threshold=params.get("conf_threshold", 0.4)
                )
                session.accidents_count = summary.get("confirmed_accidents", 0)
                if session.accidents_count > 0:
                    create_alert(
                        alert_type="Accident Alert",
                        severity="Critical",
                        module="accident",
                        description=f"Confirmed vehicle collision detected with persistent proximity overlap",
                        evidence_image=get_rel_path(summary.get("evidence_path")),
                        session_id=session_id
                    )

            elif module == "overspeed":
                summary = process_overspeed_video(
                    input_path, output_path,
                    speed_limit_kmh=params.get("speed_limit_kmh", 70),
                    calibration_factor=params.get("calibration_factor", 1.2),
                    progress_callback=progress_cb,
                    conf_threshold=params.get("conf_threshold", 0.4)
                )
                session.overspeed_count = summary.get("overspeed_violations", 0)
                if session.overspeed_count > 0:
                    create_alert(
                        alert_type="Overspeed Warning",
                        severity="High",
                        module="overspeed",
                        description=f"Detected {session.overspeed_count} overspeed violations exceeding {params.get('speed_limit_kmh', 70)} km/h limit",
                        evidence_image=get_rel_path(summary.get("evidence_path")),
                        session_id=session_id
                    )

            elif module == "drowsiness":
                summary = process_drowsiness_video(
                    input_path, output_path,
                    ear_threshold=params.get("ear_threshold", 0.23),
                    consecutive_frames_req=params.get("consecutive_frames_req", 15),
                    progress_callback=progress_cb
                )
                session.drowsiness_count = summary.get("drowsiness_incidents", 0)
                if session.drowsiness_count > 0:
                    create_alert(
                        alert_type="Drowsiness Alert",
                        severity="Critical",
                        module="drowsiness",
                        description=f"Driver eye closure detected exceeding safe threshold ({session.drowsiness_count} incidents)",
                        evidence_image=get_rel_path(summary.get("evidence_path")),
                        session_id=session_id
                    )

            duration = time.time() - start_time
            session.duration_sec = duration
            session.completed_at = datetime.utcnow()
            session.status = "COMPLETED"
            session.output_path = get_rel_path(output_path)
            session.evidence_path = get_rel_path(summary.get("evidence_path"))
            session.set_summary(summary)

            job.status = "COMPLETED"
            job.progress_percent = 100
            job.message = "Video analysis completed successfully."
            db.session.commit()

            JOB_STATUS_CACHE[job_id]["status"] = "COMPLETED"
            JOB_STATUS_CACHE[job_id]["progress_percent"] = 100
            JOB_STATUS_CACHE[job_id]["message"] = "Completed successfully."
            JOB_STATUS_CACHE[job_id]["result"] = session.to_dict()

        except Exception as e:
            db.session.rollback()
            session.status = "FAILED"
            session.error_message = str(e)
            job.status = "FAILED"
            job.message = f"Processing error: {str(e)}"
            db.session.commit()

            JOB_STATUS_CACHE[job_id]["status"] = "FAILED"
            JOB_STATUS_CACHE[job_id]["message"] = f"Error: {str(e)}"

def dispatch_video_job(app, session_id, module, input_path, output_path, params=None):
    job_id = uuid.uuid4().hex
    job = ProcessingJob(
        id=job_id,
        session_id=session_id,
        status="QUEUED",
        progress_percent=0,
        message="Queued for processing"
    )
    db.session.add(job)
    db.session.commit()

    JOB_STATUS_CACHE[job_id] = {
        "id": job_id,
        "session_id": session_id,
        "status": "QUEUED",
        "progress_percent": 0,
        "message": "Queued for processing",
        "result": None
    }

    executor.submit(run_background_job, app, job_id, session_id, module, input_path, output_path, params or {})
    return job_id
