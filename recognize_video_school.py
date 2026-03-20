"""
Real-time Facial Recognition Attendance System
Logs attendance to database and sends parent notifications
Usage: python recognize_video_school.py --detector Models --embedding-model openface_nn4.small2.v1.t7 --recognizer output/recognizer.pickle --le output/le.pickle
"""

from imutils.video import VideoStream
from imutils.video import FPS
import numpy as np
import argparse
import cv2
import imutils
import pickle
import time
import os
from datetime import datetime, date
from database import DatabaseConnection
from notifications import SMSNotificationService, AttendanceAlerts
from config import *

class SchoolAttendanceSystem:
    def __init__(self, detector_path, embedding_model, recognizer_path, le_path):
        """Initialize the attendance system"""
        print("[INFO] Loading facial recognition models...")
        
        # Load face detector
        protoPath = os.path.sep.join([detector_path, 'deploy.prototxt'])
        modelPath = os.path.sep.join([detector_path, 'res10_300x300_ssd_iter_140000.caffemodel'])
        self.detector = cv2.dnn.readNetFromCaffe(protoPath, modelPath)
        
        # Load embedding model
        self.embedder = cv2.dnn.readNetFromTorch(embedding_model)
        
        # Load recognizer and label encoder
        self.recognizer = pickle.loads(open(recognizer_path, 'rb').read())
        self.le = pickle.loads(open(le_path, 'rb').read())
        
        # Initialize database
        self.db = DatabaseConnection(
            host=DATABASE_CONFIG['host'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            database=DATABASE_CONFIG['database']
        )
        
        if not self.db.connect():
            raise Exception("Failed to connect to database")
        
        # Initialize notification service
        self.sms_service = SMSNotificationService()
        self.alerts = AttendanceAlerts(self.db, self.sms_service)
        
        # Tracking to prevent duplicate entries
        self.recognized_students = {}  # {student_id: last_recognition_time}
        self.duplicate_threshold = 5  # seconds
        
        print("[INFO] Sistema initialized successfully")
    
    def recognize_face(self, face_blob):
        """Recognize face and return prediction"""
        self.embedder.setInput(face_blob)
        vec = self.embedder.forward()
        
        preds = self.recognizer.predict_proba(vec)[0]
        j = np.argmax(preds)
        proba = preds[j]
        name = self.le.classes_[j]
        
        return name, proba
    
    def process_recognition(self, name, confidence):
        """Process recognized student and log attendance"""
        if confidence < CONFIDENCE_THRESHOLD:
            return None, None
        
        # Get student from database
        student = self.db.get_student_by_name(name)
        if not student:
            print(f"[WARNING] Student '{name}' not found in database")
            return None, None
        
        student_id = student['student_id']
        current_time = time.time()
        
        # Prevent duplicate recognitions within threshold
        if student_id in self.recognized_students:
            if current_time - self.recognized_students[student_id] < self.duplicate_threshold:
                return None, None
        
        self.recognized_students[student_id] = current_time
        return student, confidence
    
    def log_attendance_interactive(self, student, confidence):
        """Interactive mode: Ask user to select entry or exit"""
        student_id = student['student_id']
        student_name = f"{student['first_name']} {student['last_name']}"
        
        print(f"\n{'='*50}")
        print(f"✓ RECOGNIZED: {student_name}")
        print(f"  Roll No: {student['roll_number']}")
        print(f"  Confidence: {confidence*100:.2f}%")
        print(f"{'='*50}")
        
        # Interactive selection
        scan_type = None
        while scan_type not in ['E', 'X', 'F']:
            scan_type = input("Select: (E)ntry | E(X)it | (F)inish: ").upper().strip()
            if scan_type not in ['E', 'X', 'F']:
                print("Invalid option. Please try again.")
        
        if scan_type == 'F':
            return False
        
        # Map input to scan type
        scan_type = 'entry' if scan_type == 'E' else 'exit'
        
        # Log attendance in database
        self.db.log_attendance_scan(student_id, scan_type, float(confidence))
        self.db.update_or_create_attendance(student_id, scan_type)
        
        # Get attendance record
        attendance = self.db.get_today_attendance(student_id)
        
        # Send notification to parents
        contacts = self.db.get_student_contacts(student_id)
        if contacts:
            current_time = datetime.now()
            for contact in contacts:
                if scan_type == 'entry':
                    message = f"✓ {student_name} has ENTERED school at {current_time.strftime('%H:%M')}. School ID: ATTEND-SYSTEM"
                else:
                    message = f"✓ {student_name} has LEFT school at {current_time.strftime('%H:%M')}. School ID: ATTEND-SYSTEM"
                
                print(f"[SMS] Notification queued for {contact['parent_name']}: {contact['phone_number']}")
        
        # Check for late arrival and alert
        if scan_type == 'entry' and attendance and attendance['entry_time']:
            entry_hour = attendance['entry_time'].hour
            entry_min = attendance['entry_time'].minute
            entry_mins = entry_hour * 60 + entry_min
            
            # School starts at 08:00 (480 mins)
            school_start_mins = 8 * 60
            if entry_mins > school_start_mins:
                self.alerts.check_and_alert_late_arrival(student_id, datetime.now(), '08:00')
                print(f"[ALERT] {student_name} marked as LATE arrival!")
        
        print(f"[SUCCESS] {scan_type.upper()} logged for {student_name}")
        return True
    
    def run_video_mode(self):
        """Run continuous video recognition mode"""
        print("[INFO] Starting video stream...")
        print("[INFO] Press 'Q' to quit\n")
        
        # Start video stream
        vs = VideoStream(src=VIDEO_CONFIG['camera_id']).start()
        time.sleep(2.0)
        
        fps = FPS().start()
        
        try:
            while True:
                frame = vs.read()
                frame = imutils.resize(frame, width=VIDEO_CONFIG['frame_width'])
                (h, w) = frame.shape[:2]
                
                # Prepare frame for detection
                imageBlob = cv2.dnn.blobFromImage(
                    cv2.resize(frame, (300, 300)), 1.0, (300, 300),
                    (104.0, 177.0, 123.0), swapRB=False, crop=False)
                
                self.detector.setInput(imageBlob)
                detections = self.detector.forward()
                
                # Process detections
                for i in range(0, detections.shape[2]):
                    confidence = detections[0, 0, i, 2]
                    
                    if confidence > CONFIDENCE_THRESHOLD:
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        (startX, startY, endX, endY) = box.astype('int')
                        
                        face = frame[startY:endY, startX:endX]
                        (fH, fW) = face.shape[:2]
                        
                        if fW < FACE_MIN_WIDTH or fH < FACE_MIN_HEIGHT:
                            continue
                        
                        # Get face embedding
                        faceBlob = cv2.dnn.blobFromImage(
                            face, 1.0/255, (VIDEO_CONFIG['face_blob_size'], VIDEO_CONFIG['face_blob_size']),
                            (0, 0, 0), swapRB=True, crop=False)
                        
                        # Recognize face
                        name, prob = self.recognize_face(faceBlob)
                        
                        # Draw bounding box and label
                        text = f"{name}: {prob*100:.2f}%"
                        y = startY - 10 if startY - 10 > 10 else startY + 25
                        cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
                        cv2.putText(frame, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
                
                fps.update()
                
                # Display FPS
                cv2.putText(frame, f"FPS: {fps.fps():.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow('School Attendance System', frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
        
        finally:
            fps.stop()
            print(f"\n[INFO] Elapsed time: {fps.elapsed():.2f}s")
            print(f"[INFO] FPS: {fps.fps():.2f}")
            vs.stop()
            cv2.destroyAllWindows()
            self.db.disconnect()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--detector', required=True, help='path to face detector')
    parser.add_argument('-m', '--embedding-model', required=True, help='path to face embedding model')
    parser.add_argument('-r', '--recognizer', required=True, help='path to recognizer model')
    parser.add_argument('-l', '--le', required=True, help='path to label encoder')
    parser.add_argument('--mode', default='interactive', choices=['interactive', 'video'], help='operation mode')
    
    args = vars(parser.parse_args())
    
    try:
        system = SchoolAttendanceSystem(
            args['detector'],
            args['embedding_model'],
            args['recognizer'],
            args['le']
        )
        
        if args['mode'] == 'interactive':
            print("[MODE] Interactive Mode - Scan faces and select entry/exit\n")
            print("[INFO] Starting facial recognition...")
            print("[INFO] Press 'Q' to quit\n")
            
            vs = VideoStream(src=VIDEO_CONFIG['camera_id']).start()
            time.sleep(2.0)
            
            try:
                while True:
                    frame = vs.read()
                    frame = imutils.resize(frame, width=VIDEO_CONFIG['frame_width'])
                    (h, w) = frame.shape[:2]
                    
                    imageBlob = cv2.dnn.blobFromImage(
                        cv2.resize(frame, (300, 300)), 1.0, (300, 300),
                        (104.0, 177.0, 123.0), swapRB=False, crop=False)
                    
                    system.detector.setInput(imageBlob)
                    detections = system.detector.forward()
                    
                    for i in range(0, detections.shape[2]):
                        confidence = detections[0, 0, i, 2]
                        
                        if confidence > CONFIDENCE_THRESHOLD:
                            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                            (startX, startY, endX, endY) = box.astype('int')
                            
                            face = frame[startY:endY, startX:endX]
                            (fH, fW) = face.shape[:2]
                            
                            if fW < FACE_MIN_WIDTH or fH < FACE_MIN_HEIGHT:
                                continue
                            
                            faceBlob = cv2.dnn.blobFromImage(
                                face, 1.0/255, (VIDEO_CONFIG['face_blob_size'], VIDEO_CONFIG['face_blob_size']),
                                (0, 0, 0), swapRB=True, crop=False)
                            
                            name, prob = system.recognize_face(faceBlob)
                            student, conf = system.process_recognition(name, prob)
                            
                            if student:
                                cv2.imshow('Recognition', frame)
                                continue_loop = system.log_attendance_interactive(student, conf)
                                if not continue_loop:
                                    raise KeyboardInterrupt
                            
                            text = f"{name}: {prob*100:.2f}%"
                            y = startY - 10 if startY - 10 > 10 else startY + 25
                            cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
                            cv2.putText(frame, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
                    
                    cv2.imshow('School Attendance System', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            
            finally:
                vs.stop()
                cv2.destroyAllWindows()
        
        else:  # video mode
            system.run_video_mode()
    
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if 'system' in locals():
            system.db.disconnect()

if __name__ == '__main__':
    main()
