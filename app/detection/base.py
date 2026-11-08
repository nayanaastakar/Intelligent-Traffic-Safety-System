import os
import cv2
import numpy as np
from app.config import Config

VEHICLE_CLASSES = {"car", "truck", "bus", "motorbike", "bicycle"}
ALL_VEHICLE_LABELS = ["car", "truck", "bus", "motorbike", "bicycle", "traffic light", "person"]

# Color palette for classes (BGR)
CLASS_COLORS = {
    "car": (16, 185, 129),       # Emerald
    "truck": (59, 130, 246),     # Blue
    "bus": (245, 158, 11),       # Amber
    "motorbike": (168, 85, 247), # Purple
    "bicycle": (236, 72, 153),   # Pink
    "person": (20, 184, 166),    # Teal
    "default": (148, 163, 184)   # Slate
}

def play_alert_sound(freq=1000, duration=300):
    """Play alert sound on Windows safely."""
    try:
        import winsound
        winsound.Beep(freq, duration)
    except Exception:
        pass

class YOLOSingleton:
    _net = None
    _output_layers = None
    _classes = None

    @classmethod
    def load(cls):
        if cls._net is not None:
            return cls._net, cls._output_layers, cls._classes

        # Try tiny weights first, then full
        cfg = Config.YOLO_CFG
        weights = Config.YOLO_WEIGHTS
        if not os.path.exists(cfg) or not os.path.exists(weights):
            cfg = Config.YOLO_FULL_CFG
            weights = Config.YOLO_FULL_WEIGHTS

        if not os.path.exists(cfg) or not os.path.exists(weights):
            raise FileNotFoundError(f"YOLO weights or config missing at {weights}, {cfg}")

        net = cv2.dnn.readNet(weights, cfg)
        layer_names = net.getLayerNames()
        output_layers = net.getUnconnectedOutLayers()
        if isinstance(output_layers, np.ndarray):
            output_layers = output_layers.flatten()
        output_layers = [layer_names[i - 1] for i in output_layers]

        classes = []
        if os.path.exists(Config.COCO_NAMES):
            with open(Config.COCO_NAMES, "r", encoding="utf-8") as f:
                classes = [line.strip() for line in f if line.strip()]

        cls._net = net
        cls._output_layers = output_layers
        cls._classes = classes
        return cls._net, cls._output_layers, cls._classes

def draw_hud_box(frame, x, y, w, h, label, confidence, color=None):
    """Draw a modern, surveillance-style bounding box with semi-transparent label badge."""
    c = color if color else CLASS_COLORS.get(label, CLASS_COLORS["default"])
    cv2.rectangle(frame, (x, y), (x + w, y + h), c, 2)
    
    badge_text = f"{label.upper()} {int(confidence * 100)}%" if confidence else label.upper()
    (tw, th), baseline = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    
    # Label badge background
    cv2.rectangle(frame, (x, y - th - 8), (x + tw + 10, y), c, -1)
    cv2.putText(frame, badge_text, (x + 5, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (15, 23, 42), 1, cv2.LINE_AA)
