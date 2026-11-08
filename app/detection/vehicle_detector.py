import os
import cv2
import numpy as np
from app.detection.base import YOLOSingleton, VEHICLE_CLASSES, draw_hud_box
from app.config import Config

def detect_vehicles_in_image(image_path, output_path=None, conf_threshold=0.4, nms_threshold=0.4):
    """
    Perform vehicle detection and classification on a single image.
    Preserves and extends vehicle_name.py algorithm.
    """
    net, output_layers, classes = YOLOSingleton.load()
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Unable to read image at {image_path}")

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
            if confidence > conf_threshold:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                boxes.append([x, y, w, h])
                confidences.append(confidence)
                class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
    
    vehicle_counts = {}
    detected_items = []
    
    annotated = image.copy()
    
    if len(indexes) > 0:
        for i in indexes.flatten():
            label = classes[class_ids[i]] if class_ids[i] < len(classes) else "vehicle"
            conf = confidences[i]
            x, y, w, h = boxes[i]
            
            # Count detected class
            vehicle_counts[label] = vehicle_counts.get(label, 0) + 1
            
            draw_hud_box(annotated, x, y, w, h, label, conf)
            detected_items.append({
                "label": label,
                "confidence": round(conf, 3),
                "box": [x, y, w, h]
            })

    # Summary HUD Banner
    total_vehicles = sum(vehicle_counts.values())
    cv2.rectangle(annotated, (15, 15), (380, 80), (15, 23, 42), -1)
    cv2.rectangle(annotated, (15, 15), (380, 80), (51, 65, 85), 1)
    cv2.putText(annotated, "SURVEILLANCE HUD: VEHICLE CLASSIFIER", (25, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (59, 130, 246), 1, cv2.LINE_AA)
    cv2.putText(annotated, f"Total Detected: {total_vehicles}", (25, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (16, 185, 129), 2, cv2.LINE_AA)

    if output_path:
        cv2.imwrite(output_path, annotated)

    return {
        "total_vehicles": total_vehicles,
        "vehicle_counts": vehicle_counts,
        "detected_items": detected_items,
        "output_path": output_path
    }


def detect_vehicles_in_video(video_path, output_path, progress_callback=None, conf_threshold=0.4, nms_threshold=0.4):
    """
    Process an entire video for vehicle detection and counting.
    """
    net, output_layers, classes = YOLOSingleton.load()
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
    total_vehicle_detections = 0
    max_in_single_frame = 0
    vehicle_type_distribution = {}
    evidence_saved = False
    evidence_path = None

    evidence_dir = Config.EVIDENCE_FOLDER

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        
        # Optimize inference: perform full detection on sampled frames or full video
        # Tiny-v3 is fast enough for per-frame or every 2nd frame
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        outputs = net.forward(output_layers)

        boxes, confidences, class_ids = [], [], []
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = int(np.argmax(scores))
                confidence = float(scores[class_id])
                if confidence > conf_threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(confidence)
                    class_ids.append(class_id)

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
        frame_vehicles = 0

        if len(indexes) > 0:
            for i in indexes.flatten():
                label = classes[class_ids[i]] if class_ids[i] < len(classes) else "vehicle"
                if label in VEHICLE_CLASSES or label in ["person"]:
                    frame_vehicles += 1
                    vehicle_type_distribution[label] = vehicle_type_distribution.get(label, 0) + 1
                    x, y, w, h = boxes[i]
                    draw_hud_box(frame, x, y, w, h, label, confidences[i])

        total_vehicle_detections += frame_vehicles
        if frame_vehicles > max_in_single_frame:
            max_in_single_frame = frame_vehicles

        # Telemetry HUD
        cv2.rectangle(frame, (15, 15), (320, 75), (15, 23, 42), -1)
        cv2.rectangle(frame, (15, 15), (320, 75), (51, 65, 85), 1)
        cv2.putText(frame, "TRAFFIC MONITORING STREAM", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (59, 130, 246), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Active Vehicles: {frame_vehicles}", (25, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (16, 185, 129), 2, cv2.LINE_AA)

        out.write(frame)

        # Capture evidence snapshot at peak frame
        if not evidence_saved and frame_vehicles >= 3:
            evidence_path = os.path.join(evidence_dir, f"evidence_veh_{os.path.basename(video_path)}.jpg")
            cv2.imwrite(evidence_path, frame)
            evidence_saved = True

        if progress_callback and total_frames > 0:
            progress_callback(frame_idx, total_frames)

    cap.release()
    out.release()

    if not evidence_saved:
        # Fallback evidence on last frame
        evidence_path = os.path.join(evidence_dir, f"evidence_veh_{os.path.basename(video_path)}.jpg")
        if 'frame' in locals() and frame is not None:
            cv2.imwrite(evidence_path, frame)

    avg_vehicles_per_frame = (total_vehicle_detections / frame_idx) if frame_idx else 0

    return {
        "processed_frames": frame_idx,
        "total_detections": total_vehicle_detections,
        "avg_vehicles_per_frame": round(avg_vehicles_per_frame, 2),
        "peak_vehicles": max_in_single_frame,
        "vehicle_type_distribution": vehicle_type_distribution,
        "output_path": output_path,
        "evidence_path": evidence_path
    }
