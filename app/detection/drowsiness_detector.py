import os
import time
import cv2
import numpy as np
from app.detection.base import play_alert_sound
from app.config import Config

LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]

def calculate_ear(landmarks, indices):
    """Calculate Eye Aspect Ratio (EAR) from facial landmarks."""
    points = np.array([landmarks[i] for i in indices])
    A = np.linalg.norm(points[1] - points[5])
    B = np.linalg.norm(points[2] - points[4])
    C = np.linalg.norm(points[0] - points[3])
    if C == 0:
        return 0.0
    return float((A + B) / (2.0 * C))

# Global streaming controller for camera management
class CameraStreamController:
    _instance = None

    def __init__(self):
        self.is_running = False
        self.cap = None
        self.camera_index = 0
        self.ear_threshold = 0.23
        self.consecutive_required = 15
        self.latest_status = "IDLE"
        self.latest_ear = 0.0
        self.alerts_count = 0

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CameraStreamController()
        return cls._instance

    def start(self, camera_index=0, ear_threshold=0.23, consecutive_required=15):
        self.stop()
        self.camera_index = camera_index
        self.ear_threshold = ear_threshold
        self.consecutive_required = consecutive_required
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            self.cap = None
            raise RuntimeError(f"Unable to access camera device at index {camera_index}")
        self.is_running = True

    def stop(self):
        self.is_running = False
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.latest_status = "STOPPED"


def generate_drowsiness_stream():
    """MJPEG generator for live browser webcam feed with real-time MediaPipe face mesh."""
    controller = CameraStreamController.get_instance()
    if not controller.is_running or controller.cap is None:
        return

    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    consecutive_frames = 0

    while controller.is_running and controller.cap is not None and controller.cap.isOpened():
        ret, frame = controller.cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(frame_rgb)

        status = "NORMAL / AWAKE"
        color = (16, 185, 129) # Emerald
        ear = 0.0

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            points = [
                (int(l.x * frame.shape[1]), int(l.y * frame.shape[0]))
                for l in landmarks
            ]

            left_ear = calculate_ear(points, LEFT_EYE_LANDMARKS)
            right_ear = calculate_ear(points, RIGHT_EYE_LANDMARKS)
            ear = (left_ear + right_ear) / 2.0
            controller.latest_ear = round(ear, 3)

            if ear < controller.ear_threshold:
                consecutive_frames += 1
                status = "EYES CLOSED"
                color = (245, 158, 11) # Amber
            else:
                consecutive_frames = 0
                status = "NORMAL / AWAKE"
                color = (16, 185, 129)

            if consecutive_frames >= controller.consecutive_required:
                status = "DROWSINESS ALERT!"
                color = (0, 0, 255) # Red
                controller.alerts_count += 1
                play_alert_sound(900, 200)

            # Draw eye keypoints
            for idx in LEFT_EYE_LANDMARKS + RIGHT_EYE_LANDMARKS:
                if idx < len(points):
                    cv2.circle(frame, points[idx], 2, (0, 255, 255), -1)

        controller.latest_status = status

        # Surveillance HUD on stream
        cv2.rectangle(frame, (15, 15), (420, 95), (15, 23, 42), -1)
        cv2.rectangle(frame, (15, 15), (420, 95), (51, 65, 85), 1)
        cv2.putText(frame, "DRIVER VIGILANCE MONITOR", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (59, 130, 246), 1, cv2.LINE_AA)
        cv2.putText(frame, f"EAR: {ear:.2f} (Thresh: {controller.ear_threshold})", (25, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"STATUS: {status}", (25, 83), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

        # Encode to JPEG for MJPEG stream
        ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
        time.sleep(0.03)

    controller.stop()


def process_drowsiness_video(video_path, output_path, ear_threshold=0.23, consecutive_frames_req=15, progress_callback=None):
    """
    Process an uploaded video file for driver drowsiness analysis.
    """
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open video at {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_idx = 0
    consecutive_frames = 0
    drowsiness_events = 0
    ear_timeline = []
    evidence_saved = False
    evidence_path = None
    evidence_dir = Config.EVIDENCE_FOLDER

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(frame_rgb)

        status = "AWAKE"
        color = (16, 185, 129)
        ear = 0.0

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            points = [
                (int(l.x * width), int(l.y * height))
                for l in landmarks
            ]

            left_ear = calculate_ear(points, LEFT_EYE_LANDMARKS)
            right_ear = calculate_ear(points, RIGHT_EYE_LANDMARKS)
            ear = (left_ear + right_ear) / 2.0

            if ear < ear_threshold:
                consecutive_frames += 1
                status = "EYES CLOSED"
                color = (245, 158, 11)
            else:
                consecutive_frames = 0
                status = "AWAKE"
                color = (16, 185, 129)

            if consecutive_frames >= consecutive_frames_req:
                status = "DROWSINESS DETECTED"
                color = (0, 0, 255)
                if consecutive_frames == consecutive_frames_req:
                    drowsiness_events += 1

            for idx in LEFT_EYE_LANDMARKS + RIGHT_EYE_LANDMARKS:
                if idx < len(points):
                    cv2.circle(frame, points[idx], 2, (0, 255, 255), -1)

        # Telemetry HUD
        cv2.rectangle(frame, (15, 15), (420, 95), (15, 23, 42), -1)
        cv2.rectangle(frame, (15, 15), (420, 95), (51, 65, 85), 1)
        cv2.putText(frame, "DRIVER VIGILANCE TELEMETRY", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (59, 130, 246), 1, cv2.LINE_AA)
        cv2.putText(frame, f"EAR: {ear:.2f} | Drowsy Incidents: {drowsiness_events}", (25, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"STATUS: {status}", (25, 83), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

        if status == "DROWSINESS DETECTED" and not evidence_saved:
            evidence_path = os.path.join(evidence_dir, f"evidence_drowsiness_{os.path.basename(video_path)}.jpg")
            cv2.imwrite(evidence_path, frame)
            evidence_saved = True

        out.write(frame)

        if frame_idx % 5 == 0:
            ear_timeline.append({
                "frame": frame_idx,
                "timestamp_sec": round(frame_idx / fps, 1),
                "ear": round(ear, 3)
            })

        if progress_callback and total_frames > 0:
            progress_callback(frame_idx, total_frames)

    cap.release()
    out.release()

    if not evidence_saved and 'frame' in locals() and frame is not None:
        evidence_path = os.path.join(evidence_dir, f"evidence_drowsiness_{os.path.basename(video_path)}.jpg")
        cv2.imwrite(evidence_path, frame)

    return {
        "total_frames": frame_idx,
        "duration_sec": round(frame_idx / fps, 2),
        "drowsiness_incidents": drowsiness_events,
        "ear_timeline": ear_timeline,
        "output_path": output_path,
        "evidence_path": evidence_path
    }
