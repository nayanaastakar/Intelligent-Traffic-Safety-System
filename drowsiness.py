import argparse
import cv2
import numpy as np
import mediapipe as mp

LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]


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
    return parser.parse_args()


def main():
    args = parse_args()
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Unable to open the webcam. Ensure a camera is connected.")

    consecutive_frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(frame_rgb)

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            points = [
                (int(landmark.x * frame.shape[1]), int(landmark.y * frame.shape[0]))
                for landmark in landmarks
            ]

            left_ear = calculate_ear(points, LEFT_EYE_LANDMARKS)
            right_ear = calculate_ear(points, RIGHT_EYE_LANDMARKS)
            ear = (left_ear + right_ear) / 2.0

            if ear < args.threshold:
                consecutive_frames += 1
                status = "DROWSY"
                color = (0, 0, 255)
            else:
                consecutive_frames = 0
                status = "AWAKE"
                color = (0, 255, 0)

            if consecutive_frames >= args.consecutive:
                status = "SLEEPINESS ALERT"
                color = (0, 0, 255)

            cv2.putText(frame, f"EAR: {ear:.2f}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(frame, status, (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        cv2.imshow("Drowsiness Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
