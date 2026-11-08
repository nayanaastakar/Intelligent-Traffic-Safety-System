import os
import math
import cv2
import numpy as np
from app.detection.base import YOLOSingleton, VEHICLE_CLASSES, draw_hud_box, play_alert_sound
from app.config import Config

class CentroidTracker:
    def __init__(self, max_disappeared=10):
        self.next_object_id = 0
        self.objects = {} # id -> (x, y)
        self.disappeared = {} # id -> count
        self.max_disappeared = max_disappeared
        self.speeds = {} # id -> speed km/h

    def register(self, centroid):
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.speeds[self.next_object_id] = 0.0
        self.next_object_id += 1

    def deregister(self, object_id):
        if object_id in self.objects:
            del self.objects[object_id]
        if object_id in self.disappeared:
            del self.disappeared[object_id]
        if object_id in self.speeds:
            del self.speeds[object_id]

    def update(self, rects, fps=25.0, calibration_factor=1.2):
        """
        rects: list of (x, y, w, h)
        Returns: dict of object_id -> (centroid, speed_kmh)
        """
        if len(rects) == 0:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)
            return self.objects

        input_centroids = np.zeros((len(rects), 2), dtype="int")
        for i, (x, y, w, h) in enumerate(rects):
            input_centroids[i] = (int(x + w / 2), int(y + h / 2))

        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.register(input_centroids[i])
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            # Distance matrix between existing centroids and new input centroids
            D = np.linalg.norm(np.array(object_centroids)[:, np.newaxis] - input_centroids, axis=2)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows = set()
            used_cols = set()

            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue

                obj_id = object_ids[row]
                prev_c = self.objects[obj_id]
                new_c = input_centroids[col]
                dist_px = math.hypot(new_c[0] - prev_c[0], new_c[1] - prev_c[1])

                # Speed estimation approximation: pixels moved * FPS * calibration factor
                # Clearly documented as optical tracking estimation
                speed_est = dist_px * (fps / 25.0) * calibration_factor * 1.8
                # Exponential moving average filter
                self.speeds[obj_id] = round(0.6 * self.speeds.get(obj_id, speed_est) + 0.4 * speed_est, 1)

                self.objects[obj_id] = new_c
                self.disappeared[obj_id] = 0

                used_rows.add(row)
                used_cols.add(col)

            unused_rows = set(range(0, D.shape[0])).difference(used_rows)
            unused_cols = set(range(0, D.shape[1])).difference(used_cols)

            for row in unused_rows:
                obj_id = object_ids[row]
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)

            for col in unused_cols:
                self.register(input_centroids[col])

        return self.objects


def process_overspeed_image(image_path, speed_kmh=85, speed_limit_kmh=70, output_path=None):
    """
    Process image with speed overlay (preserves overspeed.py functionality).
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Unable to read image at {image_path}")

    is_overspeed = speed_kmh > speed_limit_kmh
    color = (0, 0, 255) if is_overspeed else (16, 185, 129)
    status_text = "OVERSPEED VIOLATION DETECTED" if is_overspeed else "SPEED COMPLIANT"

    # Semi-transparent HUD card
    overlay = image.copy()
    cv2.rectangle(overlay, (20, 20), (520, 150), (15, 23, 42), -1)
    cv2.addWeighted(overlay, 0.85, image, 0.15, 0, image)
    cv2.rectangle(image, (20, 20), (520, 150), (51, 65, 85), 2)

    cv2.putText(image, "TRAFFIC RADAR & SPEED TELEMETRY", (35, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (59, 130, 246), 1, cv2.LINE_AA)
    cv2.putText(image, status_text, (35, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2, cv2.LINE_AA)
    cv2.putText(image, f"Monitored Speed: {speed_kmh} km/h", (35, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(image, f"Section Speed Limit: {speed_limit_kmh} km/h (Excess: {max(0, speed_kmh - speed_limit_kmh)} km/h)", (35, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1, cv2.LINE_AA)

    if is_overspeed:
        play_alert_sound(1000, 400)

    if output_path:
        cv2.imwrite(output_path, image)

    return {
        "speed_kmh": speed_kmh,
        "speed_limit_kmh": speed_limit_kmh,
        "is_overspeed": is_overspeed,
        "excess_kmh": max(0, speed_kmh - speed_limit_kmh),
        "status": status_text,
        "output_path": output_path
    }


def process_overspeed_video(video_path, output_path, speed_limit_kmh=70, calibration_factor=1.2, progress_callback=None, conf_threshold=0.4):
    """
    Video speed monitoring using frame-to-frame vehicle tracking.
    Clearly noted limitation: optical tracking approximation without surveyed 3D road calibration.
    """
    net, output_layers, classes = YOLOSingleton.load()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open video at {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    tracker = CentroidTracker(max_disappeared=15)
    frame_idx = 0
    overspeed_violations = 0
    max_detected_speed = 0.0
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
        vehicle_rects = []

        if len(indexes) > 0:
            for i in indexes.flatten():
                label = classes[class_ids[i]] if class_ids[i] < len(classes) else "obj"
                if label in VEHICLE_CLASSES:
                    x, y, w, h = boxes[i]
                    vehicle_rects.append((x, y, w, h))

        tracker.update(vehicle_rects, fps=fps, calibration_factor=calibration_factor)

        # Draw tracking and estimated speed on detected vehicles
        current_frame_violation = False
        for (x, y, w, h) in vehicle_rects:
            cx, cy = int(x + w / 2), int(y + h / 2)
            # Find closest tracked object
            matched_id = None
            min_dist = float("inf")
            for obj_id, obj_c in tracker.objects.items():
                d = math.hypot(cx - obj_c[0], cy - obj_c[1])
                if d < min_dist and d < 50:
                    min_dist = d
                    matched_id = obj_id

            if matched_id is not None:
                speed = tracker.speeds.get(matched_id, 0.0)
                if speed > max_detected_speed:
                    max_detected_speed = speed

                is_violating = speed > speed_limit_kmh
                box_color = (0, 0, 255) if is_violating else (16, 185, 129)

                cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
                speed_badge = f"ID:{matched_id} | {speed} km/h"
                if is_violating:
                    speed_badge += " [OVERSPEED!]"
                    current_frame_violation = True

                cv2.putText(frame, speed_badge, (x, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

        if current_frame_violation:
            overspeed_violations += 1

        # Telemetry HUD
        cv2.rectangle(frame, (15, 15), (480, 95), (15, 23, 42), -1)
        cv2.rectangle(frame, (15, 15), (480, 95), (51, 65, 85), 1)
        cv2.putText(frame, "RADAR TELEMETRY: OPTICAL FLOW TRACKER", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (59, 130, 246), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Speed Limit: {speed_limit_kmh} km/h | Max Observed: {max_detected_speed:.1f} km/h", (25, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Violations Logged: {overspeed_violations} (Approx. Tracking Estimation)", (25, 83), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1, cv2.LINE_AA)

        if current_frame_violation and not evidence_saved:
            evidence_path = os.path.join(evidence_dir, f"evidence_overspeed_{os.path.basename(video_path)}.jpg")
            cv2.imwrite(evidence_path, frame)
            evidence_saved = True

        out.write(frame)

        if progress_callback and total_frames > 0:
            progress_callback(frame_idx, total_frames)

    cap.release()
    out.release()

    if not evidence_saved and 'frame' in locals() and frame is not None:
        evidence_path = os.path.join(evidence_dir, f"evidence_overspeed_{os.path.basename(video_path)}.jpg")
        cv2.imwrite(evidence_path, frame)

    return {
        "total_frames": frame_idx,
        "speed_limit_kmh": speed_limit_kmh,
        "max_detected_speed_kmh": round(max_detected_speed, 1),
        "overspeed_violations": overspeed_violations,
        "calibration_note": "Calculated via 2D centroid displacement tracking. Actual speed requires calibrated physical ground markings.",
        "output_path": output_path,
        "evidence_path": evidence_path
    }
