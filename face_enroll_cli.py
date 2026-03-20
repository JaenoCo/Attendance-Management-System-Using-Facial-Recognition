#!/usr/bin/env python3
"""
Facial Enrollment Command-Line Interface
=========================================

This script provides a command-line interface for facial recognition enrollment.
You can enroll faces, train models, and check enrollment status without the web interface.

Usage Examples:
    python face_enroll_cli.py list                          # List all students
    python face_enroll_cli.py status --student_id 1        # Check enrollment status
    python face_enroll_cli.py capture-image --student_id 1 --image path/to/image.jpg
    python face_enroll_cli.py capture-webcam --student_id 1 # Capture from webcam
    python face_enroll_cli.py train                         # Train the model
    python face_enroll_cli.py stats                         # Show enrollment stats
    python face_enroll_cli.py batch-enroll --folder path/to/folder # Batch enrollment
"""

import sys
import os
import argparse
import json
from pathlib import Path
import mysql.connector
from mysql.connector import Error
import cv2
import numpy as np
from facial_recognition import get_facial_recognition_system

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'school_attendance'
}

class FacialEnrollmentCLI:
    """Command-line interface for facial enrollment"""
    
    def __init__(self):
        """Initialize the CLI"""
        self.db_config = DB_CONFIG
        self.fr_system = None
        self.connection = None
        
    def connect_db(self):
        """Connect to database"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            print("[✓] Connected to database")
            return True
        except Error as e:
            print(f"[✗] Database connection error: {e}")
            return False
    
    def close_db(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def load_fr_system(self):
        """Load facial recognition system"""
        try:
            self.fr_system = get_facial_recognition_system()
            print("[✓] Facial recognition system loaded")
            return True
        except Exception as e:
            print(f"[✗] Failed to load facial recognition system: {e}")
            return False
    
    def get_student_by_id(self, student_id):
        """Get student information by ID"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM students WHERE student_id = %s",
                (student_id,)
            )
            student = cursor.fetchone()
            cursor.close()
            return student
        except Error as e:
            print(f"[✗] Database error: {e}")
            return None
    
    def list_students(self):
        """List all students"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT student_id, first_name, last_name, roll_number, face_registered "
                "FROM students ORDER BY student_id"
            )
            students = cursor.fetchall()
            cursor.close()
            
            if not students:
                print("[!] No students found")
                return
            
            print("\n" + "=" * 80)
            print(f"{'ID':<5} {'Roll':<12} {'Name':<30} {'Face Enrolled':<15}")
            print("=" * 80)
            
            for student in students:
                status = "✓ YES" if student['face_registered'] else "✗ NO"
                name = f"{student['first_name']} {student['last_name']}"
                print(f"{student['student_id']:<5} {student['roll_number']:<12} {name:<30} {status:<15}")
            
            print("=" * 80 + "\n")
            
        except Error as e:
            print(f"[✗] Database error: {e}")
    
    def get_status(self, student_id):
        """Check enrollment status for a student"""
        student = self.get_student_by_id(student_id)
        
        if not student:
            print(f"[✗] Student with ID {student_id} not found")
            return
        
        name = f"{student['first_name']} {student['last_name']}"
        enrolled = student['face_registered']
        status_text = "✓ ENROLLED" if enrolled else "✗ NOT ENROLLED"
        
        print(f"\n{'='*50}")
        print(f"Student: {name}")
        print(f"ID: {student['student_id']}")
        print(f"Roll Number: {student['roll_number']}")
        print(f"Status: {status_text}")
        
        if enrolled:
            has_embedding = bool(student['face_data'])
            print(f"Has Embedding: {'✓ YES' if has_embedding else '✗ NO'}")
        
        print(f"{'='*50}\n")
    
    def get_stats(self):
        """Show enrollment statistics"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Get counts
            cursor.execute("SELECT COUNT(*) as total FROM students")
            total = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as enrolled FROM students WHERE face_registered = 1")
            enrolled = cursor.fetchone()['enrolled']
            
            pending = total - enrolled
            percentage = (enrolled / total * 100) if total > 0 else 0
            
            cursor.close()
            
            print("\n" + "=" * 60)
            print("ENROLLMENT STATISTICS")
            print("=" * 60)
            print(f"Total Students:    {total}")
            print(f"Enrolled:          {enrolled}")
            print(f"Pending:           {pending}")
            print(f"Progress:          {percentage:.1f}%")
            
            # Progress bar
            bar_length = 40
            filled = int(bar_length * enrolled / total) if total > 0 else 0
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"Progress Bar:      [{bar}]")
            print("=" * 60 + "\n")
            
        except Error as e:
            print(f"[✗] Database error: {e}")
    
    def capture_from_image(self, student_id, image_path):
        """Capture face from image file"""
        student = self.get_student_by_id(student_id)
        if not student:
            print(f"[✗] Student with ID {student_id} not found")
            return False
        
        if not os.path.exists(image_path):
            print(f"[✗] Image file not found: {image_path}")
            return False
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"[✗] Failed to load image: {image_path}")
            return False
        
        student_name = f"{student['first_name']} {student['last_name']}"
        
        print(f"\n[*] Processing face for {student_name}...")
        
        # Capture face
        result = self.fr_system.capture_face_from_image(image, student_id, student_name)
        
        if result['status'] != 'success':
            print(f"[✗] {result.get('message', 'Failed to capture face')}")
            return False
        
        # Update database
        try:
            cursor = self.connection.cursor()
            face_data = json.dumps(result.get('embedding', []))
            cursor.execute(
                "UPDATE students SET face_registered = 1, face_data = %s WHERE student_id = %s",
                (face_data, student_id)
            )
            self.connection.commit()
            cursor.close()
            
            confidence = result.get('confidence', 0) * 100
            print(f"[✓] Face captured successfully")
            print(f"[✓] Confidence: {confidence:.1f}%")
            print(f"[✓] Database updated")
            print(f"[✓] Image saved to: dataset/{student_name}/")
            return True
            
        except Error as e:
            print(f"[✗] Database error: {e}")
            return False
    
    def capture_from_webcam(self, student_id):
        """Capture face from webcam"""
        student = self.get_student_by_id(student_id)
        if not student:
            print(f"[✗] Student with ID {student_id} not found")
            return False
        
        student_name = f"{student['first_name']} {student['last_name']}"
        
        print(f"\n[*] Capturing face for {student_name} from webcam...")
        print("[*] Opening webcam... (Press SPACE to capture, Q to quit)")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[✗] Failed to open webcam")
            return False
        
        captured_image = None
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("[✗] Failed to read from webcam")
                    break
                
                # Display frame
                cv2.imshow(f"Capture Face - {student_name}", frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord(' '):  # Space to capture
                    captured_image = frame
                    print("[*] Image captured!")
                    break
                elif key == ord('q'):  # Q to quit
                    print("[!] Cancelled by user")
                    break
            
            cap.release()
            cv2.destroyAllWindows()
            
            if captured_image is None:
                return False
            
            # Process captured image
            print(f"[*] Processing face...")
            result = self.fr_system.capture_face_from_image(captured_image, student_id, student_name)
            
            if result['status'] != 'success':
                print(f"[✗] {result.get('message', 'Failed to capture face')}")
                return False
            
            # Update database
            cursor = self.connection.cursor()
            face_data = json.dumps(result.get('embedding', []))
            cursor.execute(
                "UPDATE students SET face_registered = 1, face_data = %s WHERE student_id = %s",
                (face_data, student_id)
            )
            self.connection.commit()
            cursor.close()
            
            confidence = result.get('confidence', 0) * 100
            print(f"[✓] Face captured successfully")
            print(f"[✓] Confidence: {confidence:.1f}%")
            print(f"[✓] Database updated")
            print(f"[✓] Image saved to: dataset/{student_name}/")
            return True
            
        except Exception as e:
            print(f"[✗] Error: {e}")
            return False
        finally:
            cap.release()
            cv2.destroyAllWindows()
    
    def train_model(self):
        """Train facial recognition model"""
        print("\n[*] Starting model training...")
        
        try:
            result = self.fr_system.train_recognizer()
            
            if result['status'] != 'success':
                print(f"[✗] Training failed: {result.get('message', 'Unknown error')}")
                return False
            
            print(f"[✓] Model trained successfully!")
            print(f"[✓] Faces processed: {result.get('num_faces', 0)}")
            print(f"[✓] Student classes: {result.get('classes', 0)}")
            print(f"[✓] Models saved to output/")
            return True
            
        except Exception as e:
            print(f"[✗] Training error: {e}")
            return False
    
    def batch_enroll(self, folder_path):
        """Batch enroll students from a folder of images"""
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            print(f"[✗] Folder not found: {folder_path}")
            return False
        
        # Find all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        image_files = [f for f in folder_path.iterdir() 
                      if f.suffix.lower() in image_extensions]
        
        if not image_files:
            print(f"[!] No image files found in {folder_path}")
            return False
        
        print(f"\n[*] Found {len(image_files)} images to process")
        
        success_count = 0
        failed_count = 0
        
        for i, image_file in enumerate(image_files, 1):
            # Try to extract student ID from filename
            # Expected format: [student_id]_[name].jpg or similar
            filename = image_file.stem
            
            try:
                # Try to parse student_id from filename
                student_id = int(filename.split('_')[0])
                
                print(f"\n[{i}/{len(image_files)}] Processing: {image_file.name}")
                
                if self.capture_from_image(student_id, str(image_file)):
                    success_count += 1
                else:
                    failed_count += 1
                    
            except (ValueError, IndexError):
                print(f"[!] Cannot parse student ID from filename: {image_file.name}")
                print(f"    Expected format: [student_id]_[name].jpg")
                failed_count += 1
        
        print(f"\n{'='*50}")
        print(f"Batch Enrollment Complete")
        print(f"{'='*50}")
        print(f"Success: {success_count}")
        print(f"Failed: {failed_count}")
        print(f"Total: {success_count + failed_count}")
        print(f"{'='*50}\n")
        
        return failed_count == 0
    
    def run(self):
        """Run the CLI"""
        parser = argparse.ArgumentParser(
            description='Facial Enrollment Command-Line Interface',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python face_enroll_cli.py list
  python face_enroll_cli.py status --student_id 1
  python face_enroll_cli.py capture-image --student_id 1 --image photo.jpg
  python face_enroll_cli.py capture-webcam --student_id 1
  python face_enroll_cli.py train
  python face_enroll_cli.py stats
  python face_enroll_cli.py batch-enroll --folder ./photos/
            """
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        
        # list command
        subparsers.add_parser('list', help='List all students')
        
        # status command
        status_parser = subparsers.add_parser('status', help='Check enrollment status')
        status_parser.add_argument('--student_id', type=int, required=True, help='Student ID')
        
        # capture-image command
        capture_image_parser = subparsers.add_parser('capture-image', help='Capture face from image')
        capture_image_parser.add_argument('--student_id', type=int, required=True, help='Student ID')
        capture_image_parser.add_argument('--image', type=str, required=True, help='Image file path')
        
        # capture-webcam command
        capture_webcam_parser = subparsers.add_parser('capture-webcam', help='Capture face from webcam')
        capture_webcam_parser.add_argument('--student_id', type=int, required=True, help='Student ID')
        
        # train command
        subparsers.add_parser('train', help='Train facial recognition model')
        
        # stats command
        subparsers.add_parser('stats', help='Show enrollment statistics')
        
        # batch-enroll command
        batch_parser = subparsers.add_parser('batch-enroll', help='Batch enroll from folder')
        batch_parser.add_argument('--folder', type=str, required=True, help='Folder with images')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        # Connect to database
        if not self.connect_db():
            return
        
        try:
            if args.command == 'list':
                self.list_students()
            
            elif args.command == 'status':
                self.get_status(args.student_id)
            
            elif args.command == 'capture-image':
                self.load_fr_system()
                self.capture_from_image(args.student_id, args.image)
            
            elif args.command == 'capture-webcam':
                self.load_fr_system()
                self.capture_from_webcam(args.student_id)
            
            elif args.command == 'train':
                self.load_fr_system()
                self.train_model()
            
            elif args.command == 'stats':
                self.get_stats()
            
            elif args.command == 'batch-enroll':
                self.load_fr_system()
                self.batch_enroll(args.folder)
        
        finally:
            self.close_db()

def main():
    """Main entry point"""
    cli = FacialEnrollmentCLI()
    cli.run()

if __name__ == '__main__':
    main()
