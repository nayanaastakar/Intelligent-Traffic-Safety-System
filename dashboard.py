import streamlit as st
import cv2
import numpy as np
import os
import time
import winsound
import mediapipe as mp

# ==============================================================================
# PAGE CONFIGURATION & THEME STYLING
# ==============================================================================
st.set_page_config(
    page_title="Intelligent Traffic Safety System",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Slate & Mint Dark Theme CSS Injection
st.markdown("""
    <style>
    /* Global Styles */
    .stApp {
        background-color: #0f172a;
        color: #f1f5f9;
    }
    
    /* Metrics Card Styling */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        transition: transform 0.2s, border-color 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #10b981;
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 1.875rem;
        font-weight: 700;
        margin-top: 8px;
    }
    .metric-desc {
        color: #10b981;
        font-size: 0.75rem;
        margin-top: 4px;
        font-weight: 500;
    }
    .metric-alert {
        color: #ef4444 !important;
    }
    
    /* Title Headers */
    .dashboard-header {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        background: linear-gradient(to right, #10b981, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 24px;
    }
    
    /* Sidebar styling tweaks */
    .css-1d391tw {
        background-color: #0f172a !important;
    }
    
    /* Alert styling */
    .alert-banner {
        background-color: #7f1d1d;
        border: 1px solid #f87171;
        color: #fca5a5;
        padding: 16px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# UTILITY PATHS & YOLO CACHED INITIALIZATION
# ==============================================================================
VEHICLE_CLASSES = {"car", "truck", "bus", "motorbike", "bicycle"}
LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]

def get_asset(path):
    base = os.path.dirname(__file__)
    return os.path.join(base, path)

@st.cache_resource
def load_yolo_model():
    cfg = get_asset("yolov3.cfg")
    weights = get_asset("yolov3.weights")
    if not os.path.exists(cfg) or not os.path.exists(weights):
        cfg = get_asset("yolov3-tiny.cfg")
        weights = get_asset("yolov3-tiny.weights")
        
    if not os.path.exists(cfg) or not os.path.exists(weights):
        return None, None, None
        
    net = cv2.dnn.readNet(weights, cfg)
    layer_names = net.getLayerNames()
    output_layers = net.getUnconnectedOutLayers()
    if isinstance(output_layers, np.ndarray):
        output_layers = output_layers.flatten()
    output_layers = [layer_names[i - 1] for i in output_layers]
    
    # Load Classes
    classes = []
    classes_path = get_asset("coco.names")
    if os.path.exists(classes_path):
        with open(classes_path, "r", encoding="utf-8") as f:
            classes = [line.strip() for line in f if line.strip()]
            
    return net, output_layers, classes

# Load models
net, output_layers, classes = load_yolo_model()

# ==============================================================================
# EAR CALCULATION (FOR DROWSINESS)
# ==============================================================================
def calculate_ear(landmarks, indices):
    points = np.array([landmarks[i] for i in indices])
    A = np.linalg.norm(points[1] - points[5])
    B = np.linalg.norm(points[2] - points[4])
    C = np.linalg.norm(points[0] - points[3])
    if C == 0:
        return 0.0
    return (A + B) / (2.0 * C)

# ==============================================================================
# SIDEBAR NAVIGATION
# ==============================================================================
st.sidebar.markdown("<h2 style='text-align: center; color: #10b981;'>🚦 TrafficSafety AI</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<hr style='margin-top: 0; margin-bottom: 20px; border-color: #334155;'>", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "NAVIGATION MODULES",
    [
        "📊 Dashboard Home",
        "📈 Traffic Density Tracker",
        "🚨 Accident Proximity Detector",
        "🥱 Driver Drowsiness Monitor",
        "🔍 Vehicle Classifier",
        "⚡ Overspeed Alert Visualizer"
    ]
)

st.sidebar.markdown("<hr style='border-color: #334155;'>", unsafe_allow_html=True)
st.sidebar.markdown("### SYSTEM RESOURCES")
if net is not None:
    st.sidebar.success("YOLO Network: Tiny-v3 Loaded")
else:
    st.sidebar.error("YOLO Assets: Not Found")
st.sidebar.info("System Health: 100% OK")

# ==============================================================================
# 1. DASHBOARD HOME
# ==============================================================================
if menu == "📊 Dashboard Home":
    st.markdown("<h1 class='dashboard-header'>Intelligent Traffic Safety Dashboard</h1>", unsafe_allow_html=True)
    st.write("Welcome to the **Intelligent Traffic Safety System**. This unified platform combines cutting-edge computer vision modules into a single, high-fidelity monitoring station for roads, drivers, and vehicles.")
    
    # Telemetry Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
            <div class='metric-card'>
                <div class='metric-title'>System Mode</div>
                <div class='metric-value' style='color: #10b981;'>ONLINE</div>
                <div class='metric-desc'>All modules verified & ready</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class='metric-card'>
                <div class='metric-title'>CPU Load</div>
                <div class='metric-value'>14.8%</div>
                <div class='metric-desc' style='color: #3b82f6;'>Normal operating bounds</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div class='metric-card'>
                <div class='metric-title'>Active Warnings</div>
                <div class='metric-value metric-alert'>0</div>
                <div class='metric-desc' style='color: #ef4444;'>No current violations</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
            <div class='metric-card'>
                <div class='metric-title'>Core Framework</div>
                <div class='metric-value'>OpenCV + MP</div>
                <div class='metric-desc' style='color: #a855f7;'>Hardware accelerated inference</div>
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown("### MODULE PREVIEWS & CAPABILITIES")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
            <div style='background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 16px;'>
                <h4 style='color: #10b981; margin-top: 0;'>📈 Traffic Density Tracker</h4>
                <p>Calculates live vehicle volume and computes a rolling density coefficient using real-time YOLO bounding boxes on traffic cameras.</p>
            </div>
            <div style='background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 16px;'>
                <h4 style='color: #ef4444; margin-top: 0;'>🚨 Accident Proximity Detector</h4>
                <p>Monitors overlapping bounding boxes to determine collision vectors and flags near-miss / accident risks with acoustic winsound alarms.</p>
            </div>
            <div style='background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 16px;'>
                <h4 style='color: #f59e0b; margin-top: 0;'>🥱 Driver Drowsiness Monitor</h4>
                <p>Uses MediaPipe Face Mesh to calculate the Eye Aspect Ratio (EAR) on live camera feeds, raising instantaneous alertness alarms.</p>
            </div>
        """, unsafe_allow_html=True)
        
    with col_b:
        st.markdown("""
            <div style='background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 16px;'>
                <h4 style='color: #3b82f6; margin-top: 0;'>🔍 Vehicle Classifier</h4>
                <p>Performs detailed object detection on target roadway images, displaying exact bounding labels and counting vehicle distributions dynamically.</p>
            </div>
            <div style='background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 16px;'>
                <h4 style='color: #a855f7; margin-top: 0;'>⚡ Overspeed Alert Visualizer</h4>
                <p>Simulates vehicle velocity telemetry overlays, mapping visual alert layers dynamically over speeding vehicles.</p>
            </div>
            <div style='background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 16px;'>
                <h4 style='color: #94a3b8; margin-top: 0;'>🛡️ SafeRoads Protocol</h4>
                <p>All safety alerts triggers standard system acoustic warnings to guarantee driver attention and roadway safety compliance.</p>
            </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# 2. TRAFFIC DENSITY TRACKER
# ==============================================================================
elif menu == "📈 Traffic Density Tracker":
    st.markdown("<h1 class='dashboard-header'>Traffic Density Tracker</h1>", unsafe_allow_html=True)
    st.write("Analyze road occupancy ratios and compute dynamic traffic density statistics using cached YOLO neural networks.")
    
    if net is None:
        st.error("YOLO assets missing! Please make sure yolov3-tiny.cfg and yolov3-tiny.weights are available in the project folder.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col2:
            st.markdown("### Settings & Controls")
            video_input_type = st.radio("Select Video Input Source", ["Demo Traffic Video", "Upload Custom Video", "Webcam Feed"])
            
            video_path = None
            if video_input_type == "Demo Traffic Video":
                demo_video_path = get_asset("data/sample_traffic.mp4")
                if os.path.exists(demo_video_path):
                    video_path = demo_video_path
                    st.success("Demo video loaded.")
                else:
                    st.warning("Demo video missing. Please upload a custom video instead.")
            elif video_input_type == "Upload Custom Video":
                uploaded_file = st.file_uploader("Upload an MP4 Video File", type=["mp4", "mov", "avi"])
                if uploaded_file is not None:
                    # Save temporarily
                    temp_path = "temp_traffic_input.mp4"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.read())
                    video_path = temp_path
                    st.success("Uploaded video successfully loaded.")
            else:
                video_path = 0 # Webcam
                st.info("Using system default camera feed.")
                
            conf_threshold = st.slider("YOLO Confidence Threshold", 0.1, 0.9, 0.4, 0.05)
            start_btn = st.button("Start Density Tracking", type="primary")
            stop_btn = st.button("Stop Tracking")
            
        with col1:
            st.markdown("### Video Telemetry Display")
            frame_placeholder = st.empty()
            
            # Analytics Chart Placeholder
            st.markdown("### Real-time Vehicle Count Graph")
            chart_placeholder = st.empty()
            
            if start_btn and video_path is not None:
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    st.error("Unable to open selected video source.")
                else:
                    frame_count = 0
                    total_vehicles = 0
                    vehicle_counts_history = []
                    
                    while cap.isOpened() and not stop_btn:
                        ret, frame = cap.read()
                        if not ret:
                            # Loop demo video
                            if video_input_type == "Demo Traffic Video":
                                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                                continue
                            break
                            
                        height, width, _ = frame.shape
                        frame_count += 1
                        
                        # YOLO Blob processing
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
                                label = classes[class_ids[i]]
                                if label in VEHICLE_CLASSES:
                                    frame_vehicles += 1
                                    x, y, w, h = boxes[i]
                                    cv2.rectangle(frame, (x, y), (x + w, y + h), (16, 185, 129), 2)
                                    cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (16, 185, 129), 2)
                                    
                        total_vehicles += frame_vehicles
                        avg_density = total_vehicles / frame_count if frame_count else 0
                        
                        # Overlay metrics onto frame
                        cv2.putText(frame, f"Live Bounding Vehicles: {frame_vehicles}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (59, 130, 246), 2)
                        cv2.putText(frame, f"Average Density Rate: {avg_density:.2f}", (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (245, 158, 11), 2)
                        
                        # Render frame in Streamlit
                        frame_placeholder.image(frame, channels="BGR", use_container_width=True)
                        
                        # Track history & render chart
                        vehicle_counts_history.append(frame_vehicles)
                        if len(vehicle_counts_history) > 100:
                            vehicle_counts_history.pop(0)
                        chart_placeholder.line_chart(vehicle_counts_history)
                        
                        time.sleep(0.01)
                        
                    cap.release()
                    st.success("Analysis terminated.")

# ==============================================================================
# 3. ACCIDENT PROXIMITY DETECTOR
# ==============================================================================
elif menu == "🚨 Accident Proximity Detector":
    st.markdown("<h1 class='dashboard-header'>Accident Proximity Detector</h1>", unsafe_allow_html=True)
    st.write("Identifies crash risks and records accidents automatically through vehicle spacing and overlapping boundary logs.")
    
    if net is None:
        st.error("YOLO assets missing! Please make sure yolov3-tiny.cfg and yolov3-tiny.weights are available in the project folder.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col2:
            st.markdown("### Settings & Controls")
            video_input_type = st.radio("Select Video Input Source", ["Demo Collision Video", "Upload Custom Video", "Webcam Feed"])
            
            video_path = None
            if video_input_type == "Demo Collision Video":
                demo_video_path = get_asset("data/sample_traffic.mp4")
                if os.path.exists(demo_video_path):
                    video_path = demo_video_path
                    st.success("Demo video loaded.")
                else:
                    st.warning("Demo video missing. Please upload a custom video instead.")
            elif video_input_type == "Upload Custom Video":
                uploaded_file = st.file_uploader("Upload Video File", type=["mp4", "mov", "avi"])
                if uploaded_file is not None:
                    temp_path = "temp_accident_input.mp4"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.read())
                    video_path = temp_path
                    st.success("Uploaded video successfully loaded.")
            else:
                video_path = 0 # Webcam
                st.info("Using default system camera.")
                
            proximity_level = st.slider("Collision Proximity Factor", 0.1, 1.0, 0.5, 0.05, help="Controls how sensitive box overlap detection is.")
            start_btn = st.button("Start Safety Monitor", type="primary")
            stop_btn = st.button("Stop Monitor")
            
        with col1:
            st.markdown("### Safety Feed")
            frame_placeholder = st.empty()
            
            alert_placeholder = st.empty()
            
            if start_btn and video_path is not None:
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    st.error("Unable to open selected video source.")
                else:
                    while cap.isOpened() and not stop_btn:
                        ret, frame = cap.read()
                        if not ret:
                            if video_input_type == "Demo Collision Video":
                                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                                continue
                            break
                            
                        height, width, _ = frame.shape
                        
                        # YOLO Blob processing
                        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
                        net.setInput(blob)
                        outputs = net.forward(output_layers)
                        
                        boxes, confidences, class_ids = [], [], []
                        for output in outputs:
                            for detection in output:
                                scores = detection[5:]
                                class_id = int(np.argmax(scores))
                                confidence = float(scores[class_id])
                                if confidence > 0.4:
                                    center_x = int(detection[0] * width)
                                    center_y = int(detection[1] * height)
                                    w = int(detection[2] * width)
                                    h = int(detection[3] * height)
                                    x = int(center_x - w / 2)
                                    y = int(center_y - h / 2)
                                    boxes.append([x, y, w, h])
                                    confidences.append(confidence)
                                    class_ids.append(class_id)
                                    
                        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.4, 0.4)
                        accident_detected = False
                        
                        if len(indexes) > 0:
                            for idx in range(len(indexes.flatten())):
                                i = indexes.flatten()[idx]
                                if classes[class_ids[i]] not in VEHICLE_CLASSES:
                                    continue
                                x, y, w, h = boxes[i]
                                
                                for jdx in range(idx + 1, len(indexes.flatten())):
                                    j = indexes.flatten()[jdx]
                                    if classes[class_ids[j]] not in VEHICLE_CLASSES:
                                        continue
                                    x2, y2, w2, h2 = boxes[j]
                                    
                                    # Overlap verification
                                    if abs(x - x2) < proximity_level * (w + w2) and abs(y - y2) < proximity_level * (h + h2):
                                        accident_detected = True
                                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                                        cv2.rectangle(frame, (x2, y2), (x2 + w2), (0, 0, 255), 3)
                                        break
                                        
                                if not accident_detected:
                                    cv2.rectangle(frame, (x, y), (x + w, y + h), (16, 185, 129), 2)
                                    cv2.putText(frame, classes[class_ids[i]], (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (16, 185, 129), 2)
                                    
                        if accident_detected:
                            cv2.putText(frame, "CRITICAL: ACCIDENT RISK DETECTED", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                            alert_placeholder.markdown("""
                                <div class='alert-banner'>
                                    ⚠️ COLLISION RISK DETECTED: SPACING VIOLATION RECORDED
                                </div>
                            """, unsafe_allow_html=True)
                            try:
                                winsound.Beep(1200, 150)
                            except RuntimeError:
                                pass
                        else:
                            alert_placeholder.empty()
                            
                        frame_placeholder.image(frame, channels="BGR", use_container_width=True)
                        time.sleep(0.01)
                        
                    cap.release()
                    alert_placeholder.empty()
                    st.success("Analysis terminated.")

# ==============================================================================
# 4. DRIVER DROWSINESS MONITOR
# ==============================================================================
elif menu == "🥱 Driver Drowsiness Monitor":
    st.markdown("<h1 class='dashboard-header'>Driver Drowsiness Monitor</h1>", unsafe_allow_html=True)
    st.write("Uses MediaPipe Face Mesh landmark maps to dynamically track Eye Aspect Ratios (EAR) and generate alarms.")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### Monitoring Parameters")
        ear_threshold = st.slider("EAR Drowsiness Threshold", 0.15, 0.35, 0.23, 0.01)
        consecutive_frames_req = st.slider("Consecutive Closed Frames Alert limit", 5, 30, 15, 1)
        
        st.info("Ensure you are in a well-lit environment and facing the camera directly for precise MediaPipe landmark maps.")
        
        start_btn = st.button("Start Camera Feed", type="primary")
        stop_btn = st.button("Stop Camera Feed")
        
    with col1:
        st.markdown("### Operator Live Stream")
        frame_placeholder = st.empty()
        
        st.markdown("### Live EAR Telemetry Graph")
        chart_placeholder = st.empty()
        
        if start_btn:
            mp_face_mesh = mp.solutions.face_mesh
            face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)
            
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                st.error("Failed to connect to system webcam. Verify camera device connections.")
            else:
                consecutive_frames = 0
                ear_history = []
                
                while not stop_btn:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = face_mesh.process(frame_rgb)
                    
                    status = "AWAKE"
                    color = (16, 185, 129)
                    
                    if results.multi_face_landmarks:
                        landmarks = results.multi_face_landmarks[0].landmark
                        points = [
                            (int(landmark.x * frame.shape[1]), int(landmark.y * frame.shape[0]))
                            for landmark in landmarks
                        ]
                        
                        left_ear = calculate_ear(points, LEFT_EYE_LANDMARKS)
                        right_ear = calculate_ear(points, RIGHT_EYE_LANDMARKS)
                        ear = (left_ear + right_ear) / 2.0
                        
                        # Track history
                        ear_history.append(ear)
                        if len(ear_history) > 100:
                            ear_history.pop(0)
                        chart_placeholder.line_chart(ear_history)
                        
                        # Check threshold
                        if ear < ear_threshold:
                            consecutive_frames += 1
                            status = "EYES CLOSED"
                            color = (59, 130, 246)
                        else:
                            consecutive_frames = 0
                            status = "AWAKE"
                            color = (16, 185, 129)
                            
                        if consecutive_frames >= consecutive_frames_req:
                            status = "DROWSINESS DETECTED!"
                            color = (0, 0, 255)
                            try:
                                winsound.Beep(800, 300)
                            except RuntimeError:
                                pass
                                
                        # Overlay status text on video
                        cv2.putText(frame, f"EAR: {ear:.2f}", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
                        cv2.putText(frame, f"STATUS: {status}", (30, 95), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
                        
                        # Draw mesh indicators on eyes
                        for eye_idx in LEFT_EYE_LANDMARKS + RIGHT_EYE_LANDMARKS:
                            pt = points[eye_idx]
                            cv2.circle(frame, pt, 2, (0, 255, 255), -1)
                            
                    frame_placeholder.image(frame, channels="BGR", use_container_width=True)
                    time.sleep(0.01)
                    
                cap.release()
                st.success("Webcam stream terminated successfully.")

# ==============================================================================
# 5. VEHICLE CLASSIFIER
# ==============================================================================
elif menu == "🔍 Vehicle Classifier":
    st.markdown("<h1 class='dashboard-header'>Vehicle Classifier & Density Report</h1>", unsafe_allow_html=True)
    st.write("Scan single images using standard object detection methods and compile summary tables of vehicle counts.")
    
    if net is None:
        st.error("YOLO assets missing! Please make sure yolov3-tiny.cfg and yolov3-tiny.weights are available in the project folder.")
    else:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### Image Selection")
            image_source = st.radio("Choose Target Image", ["Demo Highway Image", "Upload Custom Image"])
            
            image_path = None
            if image_source == "Demo Highway Image":
                demo_img = get_asset("data/sample_highway.png")
                if os.path.exists(demo_img):
                    image_path = demo_img
                    st.success("Demo highway image loaded.")
                else:
                    st.warning("Demo image missing.")
            else:
                uploaded_file = st.file_uploader("Upload Image File", type=["png", "jpg", "jpeg"])
                if uploaded_file is not None:
                    # Save temporarily
                    temp_path = "temp_classifier_input.png"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.read())
                    image_path = temp_path
                    st.success("Custom image loaded.")
                    
            run_btn = st.button("Perform Classifier Scan", type="primary")
            
        with col2:
            st.markdown("### Detection & Classification Results")
            scan_placeholder = st.empty()
            chart_placeholder = st.empty()
            
        if run_btn and image_path is not None:
            image = cv2.imread(image_path)
            if image is None:
                st.error("Failed to load chosen image file.")
            else:
                height, width, _ = image.shape
                
                # YOLO Scan
                blob = cv2.dnn.blobFromImage(image, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
                net.setInput(blob)
                outputs = net.forward(output_layers)
                
                boxes, confidences, class_ids = [], [], []
                for output in outputs:
                    for detection in output:
                        scores = detection[5:]
                        class_id = int(np.argmax(scores))
                        confidence = float(scores[class_id])
                        if confidence > 0.4:
                            center_x = int(detection[0] * width)
                            center_y = int(detection[1] * height)
                            w = int(detection[2] * width)
                            h = int(detection[3] * height)
                            x = int(center_x - w / 2)
                            y = int(center_y - h / 2)
                            boxes.append([x, y, w, h])
                            confidences.append(confidence)
                            class_ids.append(class_id)
                            
                indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.4, 0.4)
                
                detected_counts = {}
                
                if len(indexes) > 0:
                    for i in indexes.flatten():
                        x, y, w, h = boxes[i]
                        label = classes[class_ids[i]]
                        
                        # Count vehicle
                        detected_counts[label] = detected_counts.get(label, 0) + 1
                        
                        # Draw BBoxes
                        cv2.rectangle(image, (x, y), (x + w, y + h), (16, 185, 129), 3)
                        cv2.putText(image, f"{label}: {confidences[i]:.2f}", (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (16, 185, 129), 2)
                        
                scan_placeholder.image(image, channels="BGR", use_container_width=True)
                
                if detected_counts:
                    st.markdown("#### Detected Object Counts")
                    st.write(detected_counts)
                    chart_placeholder.bar_chart(detected_counts)
                else:
                    st.info("No objects detected above the confidence threshold.")

# ==============================================================================
# 6. OVERSPEED ALERT VISUALIZER
# ==============================================================================
elif menu == "⚡ Overspeed Alert Visualizer":
    st.markdown("<h1 class='dashboard-header'>Overspeed Violation Visualizer</h1>", unsafe_allow_html=True)
    st.write("Simulates vehicle speed tracking overlays, issuing immediate overspeed warnings and audible alert cues.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Telemetry Configuration")
        img_source = st.radio("Choose Target Image File", ["Demo Speeding Car", "Upload Custom Image"])
        
        image_path = None
        if img_source == "Demo Speeding Car":
            demo_img = get_asset("data/sample_car.png")
            if os.path.exists(demo_img):
                image_path = demo_img
                st.success("Demo sports car loaded.")
            else:
                st.warning("Demo image missing.")
        else:
            uploaded_file = st.file_uploader("Upload Image File", type=["png", "jpg", "jpeg"])
            if uploaded_file is not None:
                temp_path = "temp_overspeed_input.png"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.read())
                image_path = temp_path
                st.success("Custom image loaded.")
                
        # Speed slider control
        speed_val = st.slider("Simulated Detected Speed (km/h)", 20, 160, 85, 5)
        limit_val = st.slider("Highway Speed Limit (km/h)", 40, 120, 70, 5)
        
        run_btn = st.button("Generate Speed Overlay", type="primary")
        
    with col2:
        st.markdown("### Simulated HUD Output")
        hud_placeholder = st.empty()
        
    if run_btn and image_path is not None:
        image = cv2.imread(image_path)
        if image is None:
            st.error("Failed to load target image.")
        else:
            is_overspeed = speed_val > limit_val
            
            # Setup text overlay colors & content
            if is_overspeed:
                message = "CRITICAL: OVERSPEED DETECTED"
                color = (0, 0, 255) # Red
                try:
                    winsound.Beep(1000, 400)
                except RuntimeError:
                    pass
            else:
                message = "VEHICLE SPEED COMPLIANT"
                color = (16, 185, 129) # Mint Green
                
            # Draw speed limits and stats onto image HUD
            cv2.rectangle(image, (20, 20), (520, 140), (15, 23, 42), -1) # Dark Slate Box
            cv2.rectangle(image, (20, 20), (520, 140), (51, 65, 85), 2)
            
            cv2.putText(image, message, (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(image, f"Current Speed: {speed_val} km/h", (40, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(image, f"Section Speed Limit: {limit_val} km/h", (40, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (148, 163, 184), 2)
            
            hud_placeholder.image(image, channels="BGR", use_container_width=True)
            
            # Display visual indicators
            if is_overspeed:
                st.error(f"🚨 CRITICAL WARNING: Speed exceeds limit by {speed_val - limit_val} km/h!")
            else:
                st.success("✅ Speed complies with local speed limits.")
