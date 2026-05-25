import argparse
import os
import cv2
import numpy as np
import winsound

VEHICLE_CLASSES = {"car", "truck", "bus", "motorbike", "bicycle"}


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
        default=None,
        help="Path to a video file. If omitted, the webcam is used.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    net, output_layers = load_yolo()
    classes = load_classes()

    source = args.video if args.video else 0
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video source: {source}")

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
        accident_detected = False

        if len(indexes) > 0:
            for i in indexes.flatten():
                if classes[class_ids[i]] not in VEHICLE_CLASSES:
                    continue
                x, y, w, h = boxes[i]
                for j in indexes.flatten():
                    if i == j:
                        continue
                    x2, y2, w2, h2 = boxes[j]
                    if abs(x - x2) < 0.5 * (w + w2) and abs(y - y2) < 0.5 * (h + h2):
                        accident_detected = True
                        break
                if accident_detected:
                    break

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, classes[class_ids[i]], (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if accident_detected:
            cv2.putText(frame, "Accident likely detected", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            try:
                winsound.Beep(1000, 500)
            except RuntimeError:
                pass

        cv2.imshow("Accident Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
