"""
Facial Recognition Module
Handles face detection, embedding extraction, and face recognition
"""

import cv2
import numpy as np
import pickle
import os
import time
from config import (
    FACE_DETECTOR_PATH,
    FACE_EMBEDDING_MODEL,
    RECOGNIZER_MODEL,
    LABEL_ENCODER,
    CONFIDENCE_THRESHOLD,
    FACE_MIN_WIDTH,
    FACE_MIN_HEIGHT,
)

class FacialRecognitionSystem:
    """Manage facial recognition operations"""
    
    def __init__(self):
        self.detector = None
        self.embedder = None
        self.recognizer = None
        self.le = None
        self._last_model_reload_attempt = 0.0
        self._load_models()

    def _ensure_models_loaded(self):
        """Attempt to lazy-load missing models at runtime with retry throttling."""
        if self.detector is not None and self.embedder is not None and self.recognizer is not None and self.le is not None:
            return

        now = time.time()
        if now - self._last_model_reload_attempt < 3:
            return

        self._last_model_reload_attempt = now
        self._load_models()

    def validate_models(self):
        """
        Validate that all required models are loaded and ready.
        
        Returns:
            dict: Status of model validation with details
        """
        self._ensure_models_loaded()
        
        status = {
            'detector_loaded': self.detector is not None,
            'embedder_loaded': self.embedder is not None,
            'recognizer_loaded': self.recognizer is not None,
            'label_encoder_loaded': self.le is not None,
            'all_models_ready': all([
                self.detector is not None,
                self.embedder is not None,
                self.recognizer is not None,
                self.le is not None
            ])
        }
        
        return status

    def are_models_ready(self):
        """
        Quick check if all models are ready for recognition.
        
        Returns:
            bool: True if all models are loaded, False otherwise
        """
        return all([
            self.detector is not None,
            self.embedder is not None,
            self.recognizer is not None,
            self.le is not None
        ])
    
    def _load_models(self):
        """Load face detector and embedder models with detailed error reporting"""
        try:
            # Load face detector
            proto_path = os.path.join(FACE_DETECTOR_PATH, "deploy.prototxt")
            model_path = os.path.join(FACE_DETECTOR_PATH, "res10_300x300_ssd_iter_140000.caffemodel")
            
            if os.path.exists(proto_path) and os.path.exists(model_path):
                self.detector = cv2.dnn.readNetFromCaffe(proto_path, model_path)
                print("[INFO] Face detector loaded successfully")
            else:
                missing = []
                if not os.path.exists(proto_path):
                    missing.append(f"deploy.prototxt (expected at {proto_path})")
                if not os.path.exists(model_path):
                    missing.append(f"res10_300x300_ssd_iter_140000.caffemodel (expected at {model_path})")
                print(f"[WARN] Face detector models not found: {', '.join(missing)}")
            
            # Load face embedder
            if os.path.exists(FACE_EMBEDDING_MODEL):
                self.embedder = cv2.dnn.readNetFromTorch(FACE_EMBEDDING_MODEL)
                print("[INFO] Face embedder loaded successfully")
            else:
                print(f"[WARN] Face embedder model not found (expected at {FACE_EMBEDDING_MODEL})")
            
            # Load recognizer and label encoder  
            if os.path.exists(RECOGNIZER_MODEL) and os.path.exists(LABEL_ENCODER):
                try:
                    with open(RECOGNIZER_MODEL, 'rb') as f:
                        self.recognizer = pickle.load(f)
                    with open(LABEL_ENCODER, 'rb') as f:
                        self.le = pickle.load(f)
                    print("[INFO] Recognizer and label encoder loaded successfully")
                except Exception as e:
                    print(f"[WARN] Failed to load recognizer models: {e}")
                    self.recognizer = None
                    self.le = None
            else:
                missing = []
                if not os.path.exists(RECOGNIZER_MODEL):
                    missing.append(f"recognizer.pickle (expected at {RECOGNIZER_MODEL})")
                if not os.path.exists(LABEL_ENCODER):
                    missing.append(f"le.pickle (expected at {LABEL_ENCODER})")
                print(f"[WARN] Recognizer or label encoder not found: {', '.join(missing)}")
        
        except Exception as e:
            print(f"[ERROR] Fatal error loading models: {e}")
            self.detector = None
            self.embedder = None
            self.recognizer = None
            self.le = None
    
    def detect_faces(self, frame, min_confidence=None):
        """Detect faces in a frame"""
        self._ensure_models_loaded()
        if self.detector is None:
            raise RuntimeError(
                "Face detector model not loaded. Check that Models/deploy.prototxt and "
                "Models/res10_300x300_ssd_iter_140000.caffemodel exist."
            )
        
        try:
            (h, w) = frame.shape[:2]
            blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), 
                                        (104.0, 177.0, 123.0), swapRB=False, crop=False)
            self.detector.setInput(blob)
            detections = self.detector.forward()
            
            threshold = CONFIDENCE_THRESHOLD if min_confidence is None else float(min_confidence)
            faces = []
            for i in range(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > threshold:
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")
                    faces.append({
                        'box': (startX, startY, endX, endY),
                        'confidence': confidence
                    })
            
            return faces
        except Exception as e:
            print(f"[ERROR] Error detecting faces: {e}")
            raise RuntimeError(f"Face detection failed: {str(e)}")
    
    def get_face_embedding(self, face):
        """Extract embedding from a face ROI"""
        self._ensure_models_loaded()
        if self.embedder is None:
            return None
        
        try:
            blob = cv2.dnn.blobFromImage(face, 1.0/255, (96, 96), (0, 0, 0), 
                                        swapRB=True, crop=False)
            self.embedder.setInput(blob)
            vec = self.embedder.forward()
            return vec
        except Exception as e:
            print(f"[ERROR] Error extracting embedding: {e}")
            return None
    
    def recognize_face(self, embedding):
        """Recognize a face from its embedding"""
        self._ensure_models_loaded()
        if self.recognizer is None or self.le is None:
            return None, 0
        
        try:
            pred = self.recognizer.predict_proba(embedding)
            j = np.argmax(pred)
            proba = pred[0][j]
            name = self.le.classes_[j]
            return name, proba
        except Exception as e:
            print(f"[ERROR] Error recognizing face: {e}")
            return None, 0
    
    def process_frame(self, frame):
        """Process a frame and return recognized faces"""
        self._ensure_models_loaded()
        faces_data = []
        
        try:
            detections = self.detect_faces(frame)
            
            for face_info in detections:
                box = face_info['box']
                startX, startY, endX, endY = box
                
                # Extract face ROI
                face = frame[startY:endY, startX:endX]
                if face.shape[0] < FACE_MIN_HEIGHT or face.shape[1] < FACE_MIN_WIDTH:
                    continue
                
                # Get embedding
                embedding = self.get_face_embedding(face)
                if embedding is None:
                    continue
                
                # Recognize face
                name, confidence = self.recognize_face(embedding)
                
                faces_data.append({
                    'box': box,
                    'name': name,
                    'confidence': confidence,
                    'embedding': embedding
                })
            
            return faces_data
        except Exception as e:
            print(f"[ERROR] Error processing frame: {e}")
            return []
    
    def capture_face_from_image(self, image_array, student_id=None, student_name=None, min_confidence=None):
        """Capture and extract embeddings from an image"""
        try:
            # Validate models are ready
            if not self.are_models_ready():
                model_status = self.validate_models()
                missing = []
                if not model_status['detector_loaded']:
                    missing.append("face detector")
                if not model_status['embedder_loaded']:
                    missing.append("embedder")
                if not model_status['recognizer_loaded']:
                    missing.append("recognizer")
                if not model_status['label_encoder_loaded']:
                    missing.append("label encoder")
                
                return {
                    'status': 'error',
                    'message': f'Facial recognition models not ready. Missing: {", ".join(missing)}. '
                              f'Please run training_model.py to initialize models.',
                    'details': model_status
                }

            detections = self.detect_faces(image_array, min_confidence=min_confidence)

            if not detections:
                return {
                    'status': 'error',
                    'message': 'No face detected in image'
                }

            image_h, image_w = image_array.shape[:2]
            valid_faces = []
            for detection in detections:
                box = detection.get('box')
                if not box or len(box) != 4:
                    continue

                startX = max(0, min(int(box[0]), image_w - 1))
                startY = max(0, min(int(box[1]), image_h - 1))
                endX = max(0, min(int(box[2]), image_w - 1))
                endY = max(0, min(int(box[3]), image_h - 1))

                if endX <= startX or endY <= startY:
                    continue

                face = image_array[startY:endY, startX:endX]
                if face.size == 0:
                    continue

                if face.shape[0] < FACE_MIN_HEIGHT or face.shape[1] < FACE_MIN_WIDTH:
                    continue

                embedding = self.get_face_embedding(face)
                if embedding is None:
                    continue

                valid_faces.append({
                    'box': (startX, startY, endX, endY),
                    'confidence': float(detection.get('confidence', 0.0)),
                    'embedding': embedding
                })

            if not valid_faces:
                return {
                    'status': 'error',
                    'message': 'Face detected, but could not extract face embedding'
                }

            best_face = max(valid_faces, key=lambda x: x['confidence'])

            return {
                'status': 'success',
                'embedding': best_face['embedding'].tolist() if isinstance(best_face['embedding'], np.ndarray) else best_face['embedding'],
                'confidence': best_face['confidence'],
                'box': best_face['box']
            }
        except RuntimeError as e:
            print(f"[ERROR] Runtime error during face capture: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
        except Exception as e:
            print(f"[ERROR] Error capturing face: {e}")
            return {
                'status': 'error',
                'message': f'Face capture error: {str(e)}'
            }
    
    def train_recognizer(self):
        """Train the face recognizer model
        
        Note: This is a placeholder. Actual training should be done by auto_train.py
        """
        try:
            if self.recognizer is None or self.le is None:
                return {
                    'status': 'error',
                    'message': 'Recognizer not initialized. Run training_model.py first.'
                }
            
            return {
                'status': 'success',
                'message': 'Recognizer is ready. Use auto_train.py to retrain with new faces.'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Trainer error: {str(e)}'
            }


_fr_system_instance = None


# Factory function to get facial recognition system
def get_facial_recognition_system():
    """Get or create facial recognition system instance"""
    global _fr_system_instance
    if _fr_system_instance is None:
        _fr_system_instance = FacialRecognitionSystem()
    return _fr_system_instance
