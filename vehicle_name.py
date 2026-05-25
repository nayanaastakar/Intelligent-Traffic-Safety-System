import argparse
import os
import cv2
import numpy as np


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
    parser = argparse.ArgumentParser(description="Vehicle detection and class name display using YOLO.")
    parser.add_argument("--image", required=True, help="Path to the input image.")
    return parser.parse_args()


def main():
    args = parse_args()
    if not os.path.exists(args.image):
        raise FileNotFoundError(f"Image not found: {args.image}")

    net, output_layers = load_yolo()
    classes = load_classes()

    image = cv2.imread(args.image)
    if image is None:
        raise FileNotFoundError(f"Unable to open image: {args.image}")

    height, width, _ = image.shape
    blob = cv2.dnn.blobFromImage(image, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
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
    if len(indexes) > 0:
        for i in indexes.flatten():
            x, y, w, h = boxes[i]
            label = classes[class_ids[i]]
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(image, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Vehicle Detection", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
