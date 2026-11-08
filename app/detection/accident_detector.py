import os
import cv2
import numpy as np
from app.detection.base import YOLOSingleton, VEHICLE_CLASSES, draw_hud_box, play_alert_sound
from app.config import Config

INCIDENT_STATES = {
    "MONITORING": "Monitoring",
    "POTENTIAL": "Potential Accident",
    "CONFIRMATION_PENDING": "Confirmation Pending",
    "CONFIRMED": "Confirmed Detection",
    "NO_INCIDENT": "Resolved / No Incident"
}

def detect_accidents_in_video(video_path, output_path, progress_callback=None, proximity_factor=0.5, conf_frames_required=5, conf_threshold=0.4):
    """
    Integrates accident.py algorithm with delayed confirmation state machine:
    1. Checks overlap condition: abs(x - x2) < proximity * (w + w2) and abs(y - y2) < proximity * (h + h2)
    2. Uses delayed confirmation counter across consecutive frames to verify true collision vs momentary crossing.
    3. Emits incident alert and captures evidence frame upon confirmed detection.
    """
    net, output_layers, classes = YOLOSingleton.load()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open accident video at {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_idx = 0
    collision_frames_counter = 0
    confirmed_incidents = 0
    incident_events = []
    current_state = INCIDENT_STATES["MONITORING"]
    evidence_saved = False
    evidence_path = None

    evidence_dir = Config.EVIDENCE_FOLDER

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        current_time_sec = round(frame_idx / fps, 2)

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
        overlap_detected_this_frame = False
        colliding_pair = []

        if len(indexes) > 0:
            indices = indexes.flatten()
            for idx in range(len(indices)):
                i = indices[idx]
                label_i = classes[class_ids[i]] if class_ids[i] < len(classes) else "obj"
                if label_i not in VEHICLE_CLASSES:
                    continue
                x, y, w, h = boxes[i]

                for jdx in range(idx + 1, len(indices)):
                    j = indices[jdx]
                    label_j = classes[class_ids[j]] if class_ids[j] < len(classes) else "obj"
                    if label_j not in VEHICLE_CLASSES:
                        continue
                    x2, y2, w2, h2 = boxes[j]

                    # Overlap / proximity check from accident.py
                    if abs(x - x2) < proximity_factor * (w + w2) and abs(y - y2) < proximity_factor * (h + h2):
                        overlap_detected_this_frame = True
                        colliding_pair = [(x, y, w, h, label_i), (x2, y2, w2, h2, label_j)]
                        break
                
                if overlap_detected_this_frame:
                    break
                else:
                    draw_hud_box(frame, x, y, w, h, label_i, confidences[i])

        # State Machine Transitions
        if overlap_detected_this_frame:
            collision_frames_counter += 1
            if collision_frames_counter < 3:
                current_state = INCIDENT_STATES["POTENTIAL"]
            elif collision_frames_counter < conf_frames_required:
                current_state = INCIDENT_STATES["CONFIRMATION_PENDING"]
            else:
                current_state = INCIDENT_STATES["CONFIRMED"]
                if collision_frames_counter == conf_frames_required:
                    confirmed_incidents += 1
                    play_alert_sound(1200, 400)
                    incident_events.append({
                        "frame": frame_idx,
                        "timestamp_sec": current_time_sec,
                        "type": "Accident Collision",
                        "status": "Confirmed Detection",
                        "description": f"Collision vector detected between {colliding_pair[0][4]} and {colliding_pair[1][4]}"
                    })

            # Highlight colliding vehicles in Red
            for bx, by, bw, bh, blabel in colliding_pair:
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 0, 255), 3)
                cv2.putText(frame, f"IMPACT: {blabel.upper()}", (bx, by - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        else:
            if collision_frames_counter > 0:
                collision_frames_counter = max(0, collision_frames_counter - 1)
            if collision_frames_counter == 0 and current_state != INCIDENT_STATES["CONFIRMED"]:
                current_state = INCIDENT_STATES["MONITORING"]

        # Telemetry HUD
        hud_color = (0, 0, 255) if current_state == INCIDENT_STATES["CONFIRMED"] else (
            (245, 158, 11) if current_state in [INCIDENT_STATES["POTENTIAL"], INCIDENT_STATES["CONFIRMATION_PENDING"]] else (16, 185, 129)
        )
        cv2.rectangle(frame, (15, 15), (460, 95), (15, 23, 42), -1)
        cv2.rectangle(frame, (15, 15), (460, 95), (51, 65, 85), 1)
        cv2.putText(frame, "ROAD SAFETY: ACCIDENT PROXIMITY MONITOR", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (59, 130, 246), 1, cv2.LINE_AA)
        cv2.putText(frame, f"State: {current_state}", (25, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, hud_color, 2, cv2.LINE_AA)
        cv2.putText(frame, f"Time: {current_time_sec}s | Confirmed Incidents: {confirmed_incidents}", (25, 83), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1, cv2.LINE_AA)

        if current_state == INCIDENT_STATES["CONFIRMED"] and not evidence_saved:
            evidence_path = os.path.join(evidence_dir, f"evidence_accident_{os.path.basename(video_path)}.jpg")
            cv2.imwrite(evidence_path, frame)
            evidence_saved = True

        out.write(frame)

        if progress_callback and total_frames > 0:
            progress_callback(frame_idx, total_frames)

    cap.release()
    out.release()

    if not evidence_saved and 'frame' in locals() and frame is not None:
        evidence_path = os.path.join(evidence_dir, f"evidence_accident_{os.path.basename(video_path)}.jpg")
        cv2.imwrite(evidence_path, frame)

    return {
        "total_frames": frame_idx,
        "duration_sec": round(frame_idx / fps, 2),
        "confirmed_accidents": confirmed_incidents,
        "final_state": current_state if confirmed_incidents > 0 else INCIDENT_STATES["NO_INCIDENT"],
        "incident_events": incident_events,
        "output_path": output_path,
        "evidence_path": evidence_path
    }
