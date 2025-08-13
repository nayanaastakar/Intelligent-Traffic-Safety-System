import cv2
import dlib
import numpy as np

class DrowsinessDetector:
    def __init__(self):
        # Load the pre-trained face detector and shape predictor
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        self.consecutive_drowsy_frames = 0
        self.drowsy_threshold = 15  # Number of consecutive frames to consider drowsy

    def are_eyes_closed(self, landmarks):
        # Get the coordinates of the left and right eye
        left_eye = landmarks[36:42]
        right_eye = landmarks[42:48]

        # Calculate the eye aspect ratio (EAR) for both eyes
        left_ear = self.calculate_ear(left_eye)
        right_ear = self.calculate_ear(right_eye)

        # Average EAR
        ear = (left_ear + right_ear) / 2.0

        # Check if the eyes are closed based on EAR threshold
        return ear < 0.25  # Threshold for drowsiness

    def calculate_ear(self, eye):
        # Calculate the distances between the vertical eye landmarks
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        ear = (A + B) / (2.0 * C)
        return ear

    def is_drowsy(self):
        return self.consecutive_drowsy_frames >= self.drowsy_threshold

    def reset_consecutive_frames(self):
        self.consecutive_drowsy_frames = 0

    def increment_consecutive_frames(self):
        self.consecutive_drowsy_frames += 1

def main():
    detector = DrowsinessDetector()
    video_capture = cv2.VideoCapture(0)  # Use the default camera

    while True:
        ret, frame = video_capture.read()
        if not ret:
            break

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detector(gray_frame)

        for face in faces:
            landmarks = detector.predictor(gray_frame, face)
            landmarks = np.array([[p.x, p.y] for p in landmarks.parts()])

            if detector.are_eyes_closed(landmarks):
                detector.increment_consecutive_frames()
                cv2.putText(frame, "DROWSY", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                detector.reset_consecutive_frames()
                cv2.putText(frame, "AWAKE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Drowsiness Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
