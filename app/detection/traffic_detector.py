import os
import cv2
import numpy as np
from app.detection.base import YOLOSingleton, VEHICLE_CLASSES, draw_hud_box
from app.config import Config

DENSITY_THRESHOLDS = {
    "LOW": (0, 3.0),
    "MEDIUM": (3.0, 7.0),
    "HIGH": (7.0, float("inf"))
}

def classify_density(avg_count):
    if avg_count < DENSITY_THRESHOLDS["LOW"][1]:
        return "Low Density", "Normal", (16, 185, 129)
    elif avg_count <= DENSITY_THRESHOLDS["MEDIUM"][1]:
        return "Medium Density", "Moderate", (245, 158, 11)
    else:
        return "High Density", "Congested", (239, 68, 68)

def analyze_traffic_density(video_path, output_path, progress_callback=None, conf_threshold=0.4):
    """
    Integrate and enhance traffic.py algorithm.
    Calculates rolling density, vehicle category counts, density level, and congestion warnings.
    """
    net, output_layers, classes = YOLOSingleton.load()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open traffic video at {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_idx = 0
    total_vehicles = 0
    density_timeline = []
    vehicle_counts_by_type = {}
    congestion_detected = False
    evidence_saved = False
    evidence_path = None

    evidence_dir = Config.EVIDENCE_FOLDER

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        
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

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, 0.4)
        frame_vehicles = 0

        if len(indexes) > 0:
            for i in indexes.flatten():
                label = classes[class_ids[i]] if class_ids[i] < len(classes) else "vehicle"
                if label in VEHICLE_CLASSES:
                    frame_vehicles += 1
                    vehicle_counts_by_type[label] = vehicle_counts_by_type.get(label, 0) + 1
                    x, y, w, h = boxes[i]
                    draw_hud_box(frame, x, y, w, h, label, confidences[i])

        total_vehicles += frame_vehicles
        avg_density = total_vehicles / frame_idx if frame_idx else 0
        density_label, status_text, color_bgr = classify_density(avg_density)

        if density_label == "High Density":
            congestion_detected = True

        # Telemetry HUD on frame
        cv2.rectangle(frame, (15, 15), (420, 95), (15, 23, 42), -1)
        cv2.rectangle(frame, (15, 15), (420, 95), (51, 65, 85), 1)
        cv2.putText(frame, "TRAFFIC DENSITY MONITOR", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (59, 130, 246), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Live Frame Vehicles: {frame_vehicles} | Avg: {avg_density:.2f}", (25, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Density Status: {density_label.upper()}", (25, 83), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_bgr, 2, cv2.LINE_AA)

        if density_label == "High Density":
            cv2.putText(frame, "WARNING: HEAVY CONGESTION", (25, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2, cv2.LINE_AA)

        out.write(frame)

        # Record timeline point every 5 frames
        if frame_idx % 5 == 0:
            density_timeline.append({
                "frame": frame_idx,
                "timestamp_sec": round(frame_idx / fps, 1),
                "vehicles": frame_vehicles,
                "rolling_avg": round(avg_density, 2)
            })

        # Save evidence frame if high congestion or peak
        if not evidence_saved and (frame_vehicles >= 5 or density_label == "High Density"):
            evidence_path = os.path.join(evidence_dir, f"evidence_traffic_{os.path.basename(video_path)}.jpg")
            cv2.imwrite(evidence_path, frame)
            evidence_saved = True

        if progress_callback and total_frames > 0:
            progress_callback(frame_idx, total_frames)

    cap.release()
    out.release()

    final_density = total_vehicles / frame_idx if frame_idx else 0
    final_density_label, final_status, _ = classify_density(final_density)

    if not evidence_saved:
        evidence_path = os.path.join(evidence_dir, f"evidence_traffic_{os.path.basename(video_path)}.jpg")
        if 'frame' in locals() and frame is not None:
            cv2.imwrite(evidence_path, frame)

    return {
        "total_frames": frame_idx,
        "total_vehicles_counted": total_vehicles,
        "average_density": round(final_density, 2),
        "density_classification": final_density_label,
        "congestion_status": final_status,
        "congestion_alert": congestion_detected,
        "vehicle_type_distribution": vehicle_counts_by_type,
        "density_timeline": density_timeline,
        "output_path": output_path,
        "evidence_path": evidence_path
    }
