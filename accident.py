import cv2
import numpy as np
import winsound  # Import winsound for beep sound

# Load YOLO
net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
layer_names = net.getLayerNames()

# Adjust this line to handle different OpenCV versions
output_layers_indices = net.getUnconnectedOutLayers()
if isinstance(output_layers_indices, np.ndarray):
    output_layers_indices = output_layers_indices.flatten()  # Flatten if it's a 2D array

output_layers = [layer_names[i - 1] for i in output_layers_indices]

# Load class names
def load_classes():
    with open("coco.names", "r") as f:
        classes = [line.strip() for line in f.readlines()]
    return classes

classes = load_classes()

# Load video
cap = cv2.VideoCapture(r"C:\Users\Nisar\OneDrive\Desktop\7Accident Predict\your_video.mp4")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    height, width, _ = frame.shape

    # Detecting objects
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outputs = net.forward(output_layers)

    boxes = []
    confidences = []
    class_ids = []

    for output in outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:  # Confidence threshold
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)

                # Rectangle coordinates
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # Non-max suppression
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

    # Check for accidents
    accident_detected = False
    for i in range(len(boxes)):
        if i in indexes:
            x, y, w, h = boxes[i]
            label = str(classes[class_ids[i]])
            if label in ["car", "truck", "bus"]:  # Check for vehicle classes
                # Logic to determine if an accident occurred
                for j in range(i + 1, len(boxes)):
                    if j in indexes:
                        x2, y2, w2, h2 = boxes[j]
                        if abs(x - x2) < 50 and abs(y - y2) < 50:  # Proximity check
                            accident_detected = True
                            break

    if accident_detected:
        # Display the accident message on the video
        cv2.putText(frame, "Accident occurred!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Play beep sound
        winsound.Beep(1000, 1000)  # Frequency 1000 Hz for 1000 ms

    # Display the resulting frame
    cv2.imshow("Frame", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
