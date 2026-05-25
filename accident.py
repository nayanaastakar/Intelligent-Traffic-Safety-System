import argparse
import os
import cv2
import numpy as np
import winsound
from cv_utils import BeepLimiter, should_exit, show_exit_hint

VEHICLE_CLASSES = {"car", "truck", "bus", "motorbike", "bicycle"}
ACCIDENT_CONFIRM_FRAMES = 6
STATIONARY_MOVEMENT_PX = 28
MIN_OVERLAP_RATIO = 0.08
CLOSE_DISTANCE_RATIO = 0.38


def get_asset(path):
    return os.path.join(os.path.dirname(__file__), path)


def find_yolo_files():
    cfg = get_asset("yolov3.cfg")
    weights = get_asset("yolov3.weights")
    if not os.path.exists(cfg) or not os.path.exists(weights):
        cfg = get_asset("yolov3-tiny.cfg")
        weights = get_asset("yolov3-tiny.weights")
    if not os.path.exists(cfg) or not os.path.exists(weights):
        raise FileNotFoundError(
            "YOLO config and weights files are required. Run download_assets.py or add yolov3.cfg and yolov3.weights / yolov3-tiny.weights to the repository."
        )
    return weights, cfg


def load_classes():
    path = get_asset("coco.names")
    if not os.path.exists(path):
        raise FileNotFoundError("Missing coco.names. Run download_assets.py or add coco.names to the repository.")
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_yolo():
    weights, cfg = find_yolo_files()
    net = cv2.dnn.readNet(weights, cfg)
    layer_names = net.getLayerNames()
    output_layers = net.getUnconnectedOutLayers()
    if isinstance(output_layers, np.ndarray):
        output_layers = output_layers.flatten()
    output_layers = [layer_names[i - 1] for i in output_layers]
    return net, output_layers


def parse_args():
    parser = argparse.ArgumentParser(description="Accident detection using YOLO object detection.")
    parser.add_argument(
        "--video",
        type=str,
        required=True,
        help="Path to a video file (required).",
    )
    return parser.parse_args()


def box_center(box):
    x, y, w, h = box
    return (x + w / 2.0, y + h / 2.0)


def intersection_ratio(box_a, box_b):
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    smaller_area = min(aw * ah, bw * bh)
    return intersection / smaller_area if smaller_area else 0.0


def nearest_previous_movement(center, previous_centers):
    if not previous_centers:
        return None
    return min(np.linalg.norm(np.array(center) - np.array(prev)) for prev in previous_centers)


def close_center_ratio(box_a, box_b):
    center_a = np.array(box_center(box_a))
    center_b = np.array(box_center(box_b))
    distance = np.linalg.norm(center_a - center_b)
    avg_size = ((box_a[2] + box_a[3]) + (box_b[2] + box_b[3])) / 4.0
    if avg_size == 0:
        return 0.0
    return distance / avg_size


def main():
    args = parse_args()
    net, output_layers = load_yolo()
    classes = load_classes()
    beep_limiter = BeepLimiter()

    source = args.video
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video source: {source}")

    previous_centers = []
    suspicious_frames = 0
    accident_latched = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        height, width, _ = frame.shape
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        outputs = net.forward(output_layers)

        boxes, confidences, class_ids = [], [], []
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = int(np.argmax(scores))
                confidence = float(scores[class_id])
                if confidence > 0.5:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(confidence)
                    class_ids.append(class_id)

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        vehicle_boxes = []

        if len(indexes) > 0:
            for i in indexes.flatten():
                if classes[class_ids[i]] not in VEHICLE_CLASSES:
                    continue
                x, y, w, h = boxes[i]
                vehicle_boxes.append([x, y, w, h])
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, classes[class_ids[i]], (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        current_centers = [box_center(box) for box in vehicle_boxes]
        suspicious_pair = False
        for idx, box_a in enumerate(vehicle_boxes):
            for box_b in vehicle_boxes[idx + 1:]:
                overlap = intersection_ratio(box_a, box_b)
                close_ratio = close_center_ratio(box_a, box_b)
                if overlap < MIN_OVERLAP_RATIO and close_ratio > CLOSE_DISTANCE_RATIO:
                    continue

                movement_a = nearest_previous_movement(box_center(box_a), previous_centers)
                movement_b = nearest_previous_movement(box_center(box_b), previous_centers)
                if movement_a is None or movement_b is None:
                    continue

                if movement_a <= STATIONARY_MOVEMENT_PX and movement_b <= STATIONARY_MOVEMENT_PX:
                    suspicious_pair = True
                    for bx, by, bw, bh in (box_a, box_b):
                        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 165, 255), 3)
                    break
            if suspicious_pair:
                break

        if suspicious_pair:
            suspicious_frames += 1
        else:
            suspicious_frames = max(0, suspicious_frames - 2)

        accident_latched = accident_latched or suspicious_frames >= ACCIDENT_CONFIRM_FRAMES

        if accident_latched:
            cv2.rectangle(frame, (0, 0), (width, 88), (0, 0, 180), -1)
            cv2.putText(
                frame,
                "Accident occured",
                (30, 55),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.15,
                (255, 255, 255),
                3,
            )
            if beep_limiter.ready():
                try:
                    winsound.Beep(1000, 250)
                except RuntimeError:
                    pass

        previous_centers = current_centers
        show_exit_hint(frame)
        cv2.imshow("Accident Detection", frame)
        if should_exit(1):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
