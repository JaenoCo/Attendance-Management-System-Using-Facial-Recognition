"""
Facial Recognition Module
Handles face capture, embedding extraction, and model training
Integrated with school attendance system
"""

import cv2
import numpy as np
import pickle
import os
import imutils
from imutils import paths
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
from datetime import datetime
import base64
from io import BytesIO
import json

class FacialRecognitionSystem:
    """Manage face capture and recognition"""
    
    def __init__(self, detector_path="Models", embedder_path="openface_nn4.small2.v1.t7", 
                 output_path="output"):
        self.detector_path = detector_path
        self.embedder_path = embedder_path
        self.output_path = output_path
        self.dataset_path = "dataset"
        
        # Create directories if they don't exist
        os.makedirs(self.output_path, exist_ok=True)
        os.makedirs(self.dataset_path, exist_ok=True)
        
        self.detector = None
        self.embedder = None
        self.recognizer = None
        self.le = None
        
        self._load_models()
    
    def _load_models(self):
        """Load face detector and embedder models"""
        try:
            # Load face detector
            proto_path = os.path.join(self.detector_path, "deploy.prototxt")
            model_path = os.path.join(self.detector_path, "res10_300x300_ssd_iter_140000.caffemodel")
            
            if os.path.exists(proto_path) and os.path.exists(model_path):
                self.detector = cv2.dnn.readNetFromCaffe(proto_path, model_path)
                print("[INFO] Face detector loaded successfully")
            else:
                print(f"[WARNING] Face detector models not found at {self.detector_path}")
            
            # Load face embedder
            if os.path.exists(self.embedder_path):
                self.embedder = cv2.dnn.readNetFromTorch(self.embedder_path)
                print("[INFO] Face embedder loaded successfully")
            else:
                print(f"[WARNING] Face embedder model not found at {self.embedder_path}")
            
            # Load recognizer if exists
            recognizer_path = os.path.join(self.output_path, "recognizer.pickle")
            le_path = os.path.join(self.output_path, "le.pickle")
            
            if os.path.exists(recognizer_path) and os.path.exists(le_path):
                self.recognizer = pickle.loads(open(recognizer_path, 'rb').read())
                self.le = pickle.loads(open(le_path, 'rb').read())
                print("[INFO] Trained recognizer loaded successfully")
        except Exception as e:
            print(f"[ERROR] Error loading models: {e}")
    
    def capture_face_from_image(self, image_array, student_id, student_name, num_samples=5):
        """
        Extract face embedding from image array (from webcam)
        Args:
            image_array: numpy array from webcam frame
            student_id: ID of the student
            student_name: Name of the student
            num_samples: Number of samples to capture
        Returns:
            dict with status and embedding
        """
        if self.detector is None or self.embedder is None:
            return {"status": "error", "message": "Models not loaded"}
        
        try:
            # Detect face
            (h, w) = image_array.shape[:2]
            imageBlob = cv2.dnn.blobFromImage(
                cv2.resize(image_array, (300, 300)), 1.0, (300, 300),
                (104.0, 177.0, 123.0), swapRB=False, crop=False
            )
            
            self.detector.setInput(imageBlob)
            detections = self.detector.forward()
            
            # Get strongest detection
            if detections.shape[2] == 0:
                return {"status": "error", "message": "No face detected"}
            
            # Find best detection
            best_confidence = 0
            best_box = None
            
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > best_confidence and confidence > 0.5:
                    best_confidence = confidence
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    best_box = box.astype('int')
            
            if best_box is None:
                return {"status": "error", "message": "Confidence too low"}
            
            startX, startY, endX, endY = best_box
            
            # Check face size
            fH, fW = endY - startY, endX - startX
            if fW < 20 or fH < 20:
                return {"status": "error", "message": "Face too small"}
            
            # Extract face and get embedding
            face = image_array[startY:endY, startX:endX]
            faceBlob = cv2.dnn.blobFromImage(
                face, 1.0/255, (96, 96), (0, 0, 0),
                swapRB=True, crop=False
            )
            
            self.embedder.setInput(faceBlob)
            embedding = self.embedder.forward()
            
            # Save face image
            student_dir = os.path.join(self.dataset_path, str(student_name))
            os.makedirs(student_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(student_dir, f"face_{student_id}_{timestamp}.png")
            cv2.imwrite(image_path, face)
            
            return {
                "status": "success",
                "message": "Face captured successfully",
                "embedding": embedding.tolist(),
                "confidence": float(best_confidence),
                "image_path": image_path,
                "student_id": student_id,
                "student_name": student_name
            }
        
        except Exception as e:
            return {"status": "error", "message": f"Error: {str(e)}"}
    
    def extract_embedding_from_array(self, image_array):
        """
        Extract embedding from a numpy array
        Args:
            image_array: numpy array of face image
        Returns:
            embedding vector
        """
        if self.embedder is None:
            return None
        
        try:
            faceBlob = cv2.dnn.blobFromImage(
                image_array, 1.0/255, (96, 96), (0, 0, 0),
                swapRB=True, crop=False
            )
            self.embedder.setInput(faceBlob)
            embedding = self.embedder.forward()
            return embedding
        except Exception as e:
            print(f"[ERROR] Error extracting embedding: {e}")
            return None
    
    def extract_embeddings_from_dataset(self):
        """
        Extract embeddings from all images in dataset directory
        Returns:
            dict with embeddings and names
        """
        if self.detector is None or self.embedder is None:
            print("[ERROR] Models not loaded")
            return None
        
        print("[INFO] Extracting face embeddings...")
        imagePaths = list(paths.list_images(self.dataset_path))
        
        if not imagePaths:
            print("[WARNING] No images found in dataset")
            return {"embeddings": [], "names": []}
        
        knownEmbeddings = []
        knownNames = []
        total = 0
        
        for (i, imagePath) in enumerate(imagePaths):
            print(f"[INFO] Processing image {i+1}/{len(imagePaths)}")
            
            # Extract name from path
            name = imagePath.split(os.path.sep)[-2]
            
            # Load image
            image = cv2.imread(imagePath)
            image = imutils.resize(image, width=600)
            (h, w) = image.shape[:2]
            
            # Detect face
            imageBlob = cv2.dnn.blobFromImage(
                cv2.resize(image, (300, 300)), 1.0, (300, 300),
                (104.0, 177.0, 123.0), swapRB=False, crop=False
            )
            
            self.detector.setInput(imageBlob)
            detections = self.detector.forward()
            
            # Process each detection
            for i in range(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                
                if confidence < 0.5:
                    continue
                
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype('int')
                
                # Extract face
                face = image[startY:endY, startX:endX]
                (fH, fW) = face.shape[:2]
                
                if fW < 20 or fH < 20:
                    continue
                
                # Get embedding
                faceBlob = cv2.dnn.blobFromImage(
                    face, 1.0/255, (96, 96), (0, 0, 0),
                    swapRB=True, crop=False
                )
                self.embedder.setInput(faceBlob)
                vec = self.embedder.forward()
                
                knownEmbeddings.append(vec.flatten())
                knownNames.append(name)
                total += 1
        
        print(f"[INFO] Serializing embeddings ({total} faces)...")
        
        data = {
            "embeddings": knownEmbeddings,
            "names": knownNames
        }
        
        embeddings_path = os.path.join(self.output_path, "embeddings.pickle")
        with open(embeddings_path, 'wb') as f:
            f.write(pickle.dumps(data))
        
        print(f"[INFO] Embeddings saved to {embeddings_path}")
        return data
    
    def train_recognizer(self, embeddings_data=None):
        """
        Train SVM classifier on face embeddings
        Args:
            embeddings_data: dict with 'embeddings' and 'names' keys
        Returns:
            dict with status
        """
        try:
            # Extract embeddings if not provided
            if embeddings_data is None:
                embeddings_data = self.extract_embeddings_from_dataset()
            
            if not embeddings_data or not embeddings_data['embeddings']:
                return {"status": "error", "message": "No embeddings to train on"}
            
            print("[INFO] Training face recognizer...")
            
            # Encode labels
            le = LabelEncoder()
            labels = le.fit_transform(embeddings_data['names'])
            
            # Train SVM
            recognizer = SVC(C=1.0, kernel='linear', probability=True)
            recognizer.fit(embeddings_data['embeddings'], labels)
            
            # Save models
            recognizer_path = os.path.join(self.output_path, "recognizer.pickle")
            le_path = os.path.join(self.output_path, "le.pickle")
            
            with open(recognizer_path, 'wb') as f:
                f.write(pickle.dumps(recognizer))
            
            with open(le_path, 'wb') as f:
                f.write(pickle.dumps(le))
            
            # Load models for immediate use
            self.recognizer = recognizer
            self.le = le
            
            print(f"[INFO] Recognizer trained and saved")
            return {
                "status": "success",
                "message": "Model trained successfully",
                "num_faces": len(embeddings_data['embeddings']),
                "num_classes": len(le.classes_),
                "classes": le.classes_.tolist()
            }
        
        except Exception as e:
            return {"status": "error", "message": f"Training failed: {str(e)}"}
    
    def recognize_face(self, image_array, confidence_threshold=0.5):
        """
        Recognize a face in an image
        Args:
            image_array: numpy array of image
            confidence_threshold: minimum confidence for detection
        Returns:
            dict with recognition results
        """
        if self.detector is None or self.embedder is None or self.recognizer is None:
            return {"status": "error", "message": "Models not fully loaded"}
        
        try:
            (h, w) = image_array.shape[:2]
            
            # Detect faces
            imageBlob = cv2.dnn.blobFromImage(
                cv2.resize(image_array, (300, 300)), 1.0, (300, 300),
                (104.0, 177.0, 123.0), swapRB=False, crop=False
            )
            
            self.detector.setInput(imageBlob)
            detections = self.detector.forward()
            
            results = []
            
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                
                if confidence < confidence_threshold:
                    continue
                
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype('int')
                
                # Extract face
                face = image_array[startY:endY, startX:endX]
                (fH, fW) = face.shape[:2]
                
                if fW < 20 or fH < 20:
                    continue
                
                # Get embedding
                faceBlob = cv2.dnn.blobFromImage(
                    face, 1.0/255, (96, 96), (0, 0, 0),
                    swapRB=True, crop=False
                )
                self.embedder.setInput(faceBlob)
                vec = self.embedder.forward()
                
                # Predict
                preds = self.recognizer.predict_proba(vec)[0]
                j = np.argmax(preds)
                proba = preds[j]
                name = self.le.classes_[j]
                
                results.append({
                    "name": name,
                    "confidence": float(proba),
                    "box": [int(startX), int(startY), int(endX), int(endY)]
                })
            
            return {
                "status": "success",
                "faces_found": len(results),
                "results": results
            }
        
        except Exception as e:
            return {"status": "error", "message": f"Recognition failed: {str(e)}"}


# Singleton instance
_facial_recognition_system = None

def get_facial_recognition_system():
    """Get or create facial recognition system instance"""
    global _facial_recognition_system
    if _facial_recognition_system is None:
        _facial_recognition_system = FacialRecognitionSystem()
    return _facial_recognition_system
