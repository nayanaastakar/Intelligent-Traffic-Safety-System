import argparse
import os
import cv2
import winsound


def check_speed_and_overlay_image(image_path, speed):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Unable to load image '{image_path}'. Please check the path.")

    if speed > 70:
        message = "Overspeed Alert: Slow down"
        try:
            winsound.Beep(1000, 500)
        except RuntimeError:
            pass
        color = (0, 0, 255)
    else:
        message = "Speed OK"
        color = (0, 255, 0)

    font = cv2.FONT_HERSHEY_SIMPLEX
    position = (30, 50)
    cv2.putText(image, message, position, font, 1, color, 2)
    cv2.putText(image, f"Speed: {speed} km/h", (30, 90), font, 0.9, (255, 255, 255), 2)

    cv2.imshow("Overspeed Detection", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def parse_args():
    parser = argparse.ArgumentParser(description="Overlay speed messages on an image.")
    parser.add_argument("--image", required=True, help="Path to the image file.")
    parser.add_argument("--speed", type=float, default=0, help="Detected speed in km/h.")
    return parser.parse_args()


def main():
    args = parse_args()
    if not os.path.exists(args.image):
        raise FileNotFoundError(f"Image not found: {args.image}")
    check_speed_and_overlay_image(args.image, args.speed)


if __name__ == "__main__":
    main()
