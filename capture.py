
import cv2
import os
import sys
import pickle
import numpy as np

# Try to import config, fallback to defaults if not found
try:
    from config import FACE_DETECTOR_PATH, CONFIDENCE_THRESHOLD
except (ImportError, ModuleNotFoundError):
    print("[WARNING] config.py not found, using defaults")
    FACE_DETECTOR_PATH = "Models"
    CONFIDENCE_THRESHOLD = 0.5

# Load face detector
detector_proto = os.path.join(FACE_DETECTOR_PATH, 'deploy.prototxt')
detector_model = os.path.join(FACE_DETECTOR_PATH, 'res10_300x300_ssd_iter_140000.caffemodel')

# Check if detector files exist
if not os.path.exists(detector_proto) or not os.path.exists(detector_model):
    print(f"[ERROR] Face detector models not found at {FACE_DETECTOR_PATH}")
    print(f"[ERROR] Expected files:")
    print(f"  - {detector_proto}")
    print(f"  - {detector_model}")
    sys.exit(1)

print("[INFO] Loading face detector...")
detector = cv2.dnn.readNetFromCaffe(detector_proto, detector_model)

# Load face embedder
embedder_path = "openface_nn4.small2.v1.t7"
if not os.path.exists(embedder_path):
    print(f"[WARNING] Face embedder not found at {embedder_path}")
    print("[WARNING] Will show detection confidence only (no name matching)")
    embedder = None
else:
    print("[INFO] Loading face embedder...")
    embedder = cv2.dnn.readNetFromTorch(embedder_path)

# Load recognizer and label encoder
recognizer = None
le = None
recognizer_path = "output/recognizer.pickle"
le_path = "output/le.pickle"

if os.path.exists(recognizer_path) and os.path.exists(le_path):
    print("[INFO] Loading recognizer and label encoder...")
    try:
        with open(recognizer_path, 'rb') as f:
            recognizer = pickle.load(f)
        with open(le_path, 'rb') as f:
            le = pickle.load(f)
        print("[INFO] Face recognition enabled - will show student names")
    except Exception as e:
        print(f"[WARNING] Could not load recognizer: {e}")
        print("[WARNING] Will show detection confidence only")
else:
    print("[WARNING] Recognizer not found. Will show detection confidence only.")
    print(f"[INFO] To enable name matching, train the model first using training_model.py")

cam = cv2.VideoCapture(0)

if not cam.isOpened():
    print("[ERROR] Cannot open camera. Please check camera connection.")
    sys.exit(1)

cv2.namedWindow("Facial Recognition Capture")

img_counter = 0

print("[INFO] Camera started")
print("[INFO] Instructions:")
print("  - SPACE: Capture frame to dataset/sameer/")
print("  - ESC: Exit")
print(f"  - Confidence threshold: {CONFIDENCE_THRESHOLD*100:.0f}%")

while True:
    ret, frame = cam.read()
    if not ret:
        print("[ERROR] Failed to read frame from camera")
        break
    
    # Get frame dimensions
    (h, w) = frame.shape[:2]
    
    # Prepare blob for face detection
    blob = cv2.dnn.blobFromImage(
        cv2.resize(frame, (300, 300)), 1.0, (300, 300),
        (104.0, 177.0, 123.0), swapRB=False, crop=False
    )
    
    # Detect faces
    detector.setInput(blob)
    detections = detector.forward()
    
    # Process detections
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        
        # Filter by confidence threshold
        if confidence > CONFIDENCE_THRESHOLD:
            # Get bounding box coordinates
            box = detections[0, 0, i, 3:7] * [w, h, w, h]
            (startX, startY, endX, endY) = box.astype('int')
            
            # Ensure coordinates are within frame bounds
            startX = max(0, startX)
            startY = max(0, startY)
            endX = min(w, endX)
            endY = min(h, endY)
            
            # Extract face region
            face = frame[startY:endY, startX:endX]
            (fH, fW) = face.shape[:2]
            
            # Minimum face size
            if fW < 20 or fH < 20:
                continue
            
            # Initialize label with detection confidence
            label = f"Face: {confidence*100:.2f}%"
            color = (0, 255, 0)  # Green for detection
            
            # Try to recognize the face if models are loaded
            if embedder is not None and recognizer is not None and le is not None:
                try:
                    # Get face embedding
                    face_blob = cv2.dnn.blobFromImage(
                        face, 1.0/255, (96, 96), (0, 0, 0),
                        swapRB=True, crop=False
                    )
                    embedder.setInput(face_blob)
                    embedding = embedder.forward()
                    
                    # Predict identity
                    preds = recognizer.predict_proba(embedding)[0]
                    j = np.argmax(preds)
                    proba = preds[j]
                    name = le.classes_[j]
                    
                    # Update label with name and confidence
                    label = f"{name}: {proba*100:.2f}%"
                    color = (0, 255, 0) if proba > 0.6 else (0, 165, 255)  # Green for high confidence, orange for low
                    
                except Exception as e:
                    # If recognition fails, just use detection confidence
                    pass
            
            # Draw bounding box
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
            
            # Add label above bounding box
            label_y = startY - 10 if startY - 10 > 10 else startY + 25
            cv2.putText(
                frame, label, (startX, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
            )
    
    cv2.imshow("Facial Recognition Capture", frame)
    k = cv2.waitKey(1)

    if k % 256 == 27:
        # ESC pressed
        print("[INFO] Escape hit, closing...")
        break
    elif k % 256 == 32:
        # SPACE pressed
        # Create directory if it doesn't exist
        os.makedirs("dataset/sameer", exist_ok=True)
        img_name = "opencv_frame_{}.png".format(img_counter)
        cv2.imwrite(os.path.join("dataset/sameer", img_name), frame)
        print(f"[SUCCESS] {img_name} captured and saved!")
        img_counter += 1

# Clean up resources
cam.release()
cv2.destroyAllWindows()
print("[INFO] Camera closed")