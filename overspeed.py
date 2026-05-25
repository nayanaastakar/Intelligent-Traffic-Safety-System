import argparse
import os
import cv2
import winsound
from cv_utils import BeepLimiter, should_exit, show_exit_hint


def overlay_speed(frame, speed, beep_limiter):
    if speed > 70:
        message = "Overspeed Alert: Slow down"
        if beep_limiter.ready():
            try:
                winsound.Beep(1000, 250)
            except RuntimeError:
                pass
        color = (0, 0, 255)
    else:
        message = "Speed OK"
        color = (0, 255, 0)

    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, message, (30, 50), font, 1, color, 2)
    cv2.putText(frame, f"Speed: {speed} km/h", (30, 90), font, 0.9, (255, 255, 255), 2)
    return frame


def parse_args():
    parser = argparse.ArgumentParser(description="Overlay speed messages on an image or video.")
    parser.add_argument("--image", type=str, default=None, help="Path to the image file.")
    parser.add_argument("--video", type=str, default=None, help="Path to the video file.")
    parser.add_argument("--speed", type=float, default=0, help="Detected speed in km/h.")
    return parser.parse_args()


def main():
    args = parse_args()
    beep_limiter = BeepLimiter()
    if not args.image and not args.video:
        raise ValueError("Specify either --image or --video")
    if args.image and args.video:
        raise ValueError("Specify either --image or --video, not both")

    if args.image:
        if not os.path.exists(args.image):
            raise FileNotFoundError(f"Image not found: {args.image}")
        image = cv2.imread(args.image)
        if image is None:
            raise FileNotFoundError(f"Unable to load image '{args.image}'. Please check the path.")
        processed = overlay_speed(image, args.speed, beep_limiter)
        show_exit_hint(processed)
        cv2.imshow("Overspeed Detection", processed)
        while not should_exit(50):
            pass
        cv2.destroyAllWindows()
    else:
        if not os.path.exists(args.video):
            raise FileNotFoundError(f"Video not found: {args.video}")
        cap = cv2.VideoCapture(args.video)
        if not cap.isOpened():
            raise RuntimeError(f"Unable to open video: {args.video}")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            processed = overlay_speed(frame, args.speed, beep_limiter)
            show_exit_hint(processed)
            cv2.imshow("Overspeed Detection", processed)
            if should_exit(1):
                break
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
