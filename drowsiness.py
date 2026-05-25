import argparse
import os
import cv2
import numpy as np
from cv_utils import should_exit, show_exit_hint

LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]
DEFAULT_DRIVER_VIDEO = os.path.join(os.path.dirname(__file__), "uploads", "video5.mp4")


def calculate_ear(landmarks, indices):
    points = np.array([landmarks[i] for i in indices])
    A = np.linalg.norm(points[1] - points[5])
    B = np.linalg.norm(points[2] - points[4])
    C = np.linalg.norm(points[0] - points[3])
    if C == 0:
        return 0.0
    return (A + B) / (2.0 * C)


def parse_args():
    parser = argparse.ArgumentParser(description="Drowsiness detection using MediaPipe face landmarks.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.23,
        help="Eye aspect ratio threshold for drowsiness detection.",
    )
    parser.add_argument(
        "--consecutive",
        type=int,
        default=15,
        help="Number of consecutive frames below threshold before raising an alert.",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera device index (default: 0 for primary camera).",
    )
    parser.add_argument(
        "--video",
        type=str,
        default=None,
        help="Path to a driver video file. When provided, this is used instead of the camera.",
    )
    return parser.parse_args()


def load_face_mesh():
    try:
        import mediapipe as mp

        if not hasattr(mp, "solutions"):
            return None, "MediaPipe solutions API is not available in this installed version."

        return mp.solutions.face_mesh.FaceMesh(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ), None
    except Exception as exc:
        return None, f"MediaPipe unavailable: {exc}"


def open_capture(args):
    sources = []
    if args.video:
        sources.append(("video", args.video))
        sources.append(("camera", args.camera))
    else:
        sources.append(("camera", args.camera))
        if os.path.exists(DEFAULT_DRIVER_VIDEO):
            sources.append(("video", DEFAULT_DRIVER_VIDEO))

    last_error = None
    for source_type, source in sources:
        if source_type == "video" and not os.path.exists(source):
            last_error = f"Video not found: {source}"
            continue

        cap = cv2.VideoCapture(source)
        if cap.isOpened():
            return cap, source_type, source

        cap.release()
        last_error = f"Unable to open {source_type}: {source}"

    raise RuntimeError(last_error or "Unable to open camera or video source.")


def process_with_mediapipe(frame, face_mesh, consecutive_frames, threshold, consecutive_limit):
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(frame_rgb)

    if not results.multi_face_landmarks:
        cv2.putText(frame, "NO FACE", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
        return 0

    landmarks = results.multi_face_landmarks[0].landmark
    points = [
        (int(landmark.x * frame.shape[1]), int(landmark.y * frame.shape[0]))
        for landmark in landmarks
    ]

    left_ear = calculate_ear(points, LEFT_EYE_LANDMARKS)
    right_ear = calculate_ear(points, RIGHT_EYE_LANDMARKS)
    ear = (left_ear + right_ear) / 2.0

    if ear < threshold:
        consecutive_frames += 1
        status = "DROWSY"
        color = (0, 0, 255)
    else:
        consecutive_frames = 0
        status = "AWAKE"
        color = (0, 255, 0)

    if consecutive_frames >= consecutive_limit:
        status = "SLEEPINESS ALERT"
        color = (0, 0, 255)

    cv2.putText(frame, f"EAR: {ear:.2f}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(frame, status, (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    return consecutive_frames


def process_with_haar(frame, face_cascade, eye_cascade, consecutive_frames, consecutive_limit):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))

    if len(faces) == 0:
        cv2.putText(frame, "NO FACE", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
        return 0

    x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
    roi_gray = gray[y:y + h, x:x + w]
    upper_face = roi_gray[: h // 2, :]
    eyes = eye_cascade.detectMultiScale(upper_face, 1.1, 4, minSize=(18, 18))

    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 180, 255), 2)
    for ex, ey, ew, eh in eyes[:2]:
        cv2.rectangle(frame, (x + ex, y + ey), (x + ex + ew, y + ey + eh), (0, 255, 0), 2)

    if len(eyes) < 2:
        consecutive_frames += 1
        status = "DROWSY"
        color = (0, 0, 255)
    else:
        consecutive_frames = 0
        status = "AWAKE"
        color = (0, 255, 0)

    if consecutive_frames >= consecutive_limit:
        status = "SLEEPINESS ALERT"
        color = (0, 0, 255)

    cv2.putText(frame, f"Eyes: {len(eyes)}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(frame, status, (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    return consecutive_frames


def main():
    args = parse_args()
    face_mesh, mediapipe_warning = load_face_mesh()
    face_cascade = eye_cascade = None
    if face_mesh is None:
        print(f"{mediapipe_warning} Falling back to OpenCV Haar detection.", flush=True)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
        if face_cascade.empty() or eye_cascade.empty():
            raise RuntimeError("Unable to load OpenCV Haar cascades for fallback drowsiness detection.")

    cap, source_type, source = open_capture(args)
    print(f"Drowsiness detection using {source_type}: {source}", flush=True)

    consecutive_frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if face_mesh is not None:
            consecutive_frames = process_with_mediapipe(
                frame,
                face_mesh,
                consecutive_frames,
                args.threshold,
                args.consecutive,
            )
        else:
            consecutive_frames = process_with_haar(
                frame,
                face_cascade,
                eye_cascade,
                consecutive_frames,
                args.consecutive,
            )

        show_exit_hint(frame)
        cv2.imshow("Drowsiness Detection", frame)
        if should_exit(1):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
