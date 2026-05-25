import argparse
import os
import cv2
import numpy as np
from cv_utils import should_exit, show_exit_hint

ASSET_NAMES = {
    "yolov3.cfg": "https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg",
    "yolov3-tiny.cfg": "https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg",
    "coco.names": "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names",
}

VEHICLE_CLASSES = {"car", "truck", "bus", "motorbike", "bicycle"}


def get_asset(path):
    base = os.path.dirname(__file__)
    return os.path.join(base, path)


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
    parser = argparse.ArgumentParser(description="Traffic density detection using YOLO.")
    parser.add_argument(
        "--video",
        type=str,
        required=True,
        help="Path to a traffic video file (required).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    net, output_layers = load_yolo()
    classes = load_classes()

    video_source = args.video
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video source: {video_source}")

    frame_count = 0
    total_vehicles = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        height, width, _ = frame.shape
        frame_count += 1

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
        frame_vehicles = 0
        if len(indexes) > 0:
            for i in indexes.flatten():
                label = classes[class_ids[i]]
                if label in VEHICLE_CLASSES:
                    frame_vehicles += 1
                    x, y, w, h = boxes[i]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        total_vehicles += frame_vehicles
        traffic_density = total_vehicles / frame_count if frame_count else 0
        cv2.putText(frame, f"Traffic Density Avg: {traffic_density:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        show_exit_hint(frame)
        cv2.imshow("Traffic Density Tracker", frame)
        if should_exit(1):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
