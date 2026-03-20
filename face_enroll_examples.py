#!/usr/bin/env python3
"""
Facial Enrollment - Programmatic Usage Examples
================================================

This script demonstrates how to use the facial recognition system
programmatically from Python code.

You can import and use the functions directly in your own scripts.
"""

import json
import mysql.connector
from pathlib import Path
import cv2
from facial_recognition import get_facial_recognition_system

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'school_attendance'
}

class FacialEnrollmentAPI:
    """Programmatic API for facial enrollment"""
    
    def __init__(self):
        """Initialize the API"""
        self.db_config = DB_CONFIG
        self.connection = None
        self.fr_system = get_facial_recognition_system()
    
    def connect(self):
        """Connect to database"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            print("✓ Database connected")
            return True
        except Exception as e:
            print(f"✗ Database error: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def enroll_face_from_image(self, student_id, image_path):
        """
        Enroll a face for a student from an image file
        
        Args:
            student_id (int): Student ID
            image_path (str): Path to image file
        
        Returns:
            dict: Result with status, confidence, and message
        
        Example:
            api = FacialEnrollmentAPI()
            api.connect()
            result = api.enroll_face_from_image(1, 'path/to/photo.jpg')
            print(result)
            api.close()
        """
        # Get student info
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()
        cursor.close()
        
        if not student:
            return {'status': 'error', 'message': f'Student {student_id} not found'}
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            return {'status': 'error', 'message': f'Cannot load image: {image_path}'}
        
        # Capture face
        student_name = f"{student['first_name']} {student['last_name']}"
        result = self.fr_system.capture_face_from_image(image, student_id, student_name)
        
        if result['status'] != 'success':
            return result
        
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
            
            result['message'] = f'Face enrolled for {student_name}'
            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def enroll_face_from_array(self, student_id, image_array):
        """
        Enroll a face for a student from a numpy array (e.g., from OpenCV)
        
        Args:
            student_id (int): Student ID
            image_array (numpy.ndarray): Image as numpy array
        
        Returns:
            dict: Result with status and confidence
        
        Example:
            api = FacialEnrollmentAPI()
            api.connect()
            
            # Capture from webcam
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            
            result = api.enroll_face_from_array(1, frame)
            print(result)
            api.close()
        """
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()
        cursor.close()
        
        if not student:
            return {'status': 'error', 'message': f'Student {student_id} not found'}
        
        student_name = f"{student['first_name']} {student['last_name']}"
        result = self.fr_system.capture_face_from_image(image_array, student_id, student_name)
        
        if result['status'] != 'success':
            return result
        
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
            
            result['message'] = f'Face enrolled for {student_name}'
            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_enrollment_status(self, student_id):
        """
        Get enrollment status for a student
        
        Returns:
            dict: Status information
        
        Example:
            api = FacialEnrollmentAPI()
            api.connect()
            status = api.get_enrollment_status(1)
            print(f"Student {status['name']}: {status['enrolled']}")
            api.close()
        """
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT student_id, first_name, last_name, face_registered, face_data FROM students WHERE student_id = %s",
            (student_id,)
        )
        student = cursor.fetchone()
        cursor.close()
        
        if not student:
            return {'status': 'error', 'message': f'Student {student_id} not found'}
        
        return {
            'status': 'success',
            'student_id': student['student_id'],
            'name': f"{student['first_name']} {student['last_name']}",
            'enrolled': bool(student['face_registered']),
            'has_embedding': bool(student['face_data'])
        }
    
    def get_enrollment_stats(self):
        """
        Get overall enrollment statistics
        
        Returns:
            dict: Statistics
        
        Example:
            api = FacialEnrollmentAPI()
            api.connect()
            stats = api.get_enrollment_stats()
            print(f"Enrolled: {stats['enrolled']}/{stats['total']}")
            api.close()
        """
        cursor = self.connection.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as total FROM students")
        total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as enrolled FROM students WHERE face_registered = 1")
        enrolled = cursor.fetchone()['enrolled']
        
        cursor.close()
        
        percentage = (enrolled / total * 100) if total > 0 else 0
        
        return {
            'status': 'success',
            'total_students': total,
            'enrolled': enrolled,
            'pending': total - enrolled,
            'percentage': round(percentage, 1)
        }
    
    def train_model(self):
        """
        Train the facial recognition model
        
        Returns:
            dict: Training result
        
        Example:
            api = FacialEnrollmentAPI()
            api.connect()
            result = api.train_model()
            print(f"Model trained on {result['num_faces']} faces")
            api.close()
        """
        return self.fr_system.train_recognizer()
    
    def get_all_students(self):
        """
        Get list of all students with enrollment status
        
        Returns:
            list: List of student dicts
        
        Example:
            api = FacialEnrollmentAPI()
            api.connect()
            students = api.get_all_students()
            for student in students:
                print(f"{student['name']}: {'Enrolled' if student['enrolled'] else 'Pending'}")
            api.close()
        """
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT student_id, first_name, last_name, roll_number, face_registered FROM students ORDER BY student_id"
        )
        students = cursor.fetchall()
        cursor.close()
        
        return [
            {
                'student_id': s['student_id'],
                'name': f"{s['first_name']} {s['last_name']}",
                'roll_number': s['roll_number'],
                'enrolled': bool(s['face_registered'])
            }
            for s in students
        ]

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_1_enroll_from_image():
    """Example 1: Enroll a face from an image file"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Enroll Face from Image File")
    print("="*60)
    
    api = FacialEnrollmentAPI()
    if not api.connect():
        return
    
    # Enroll student 1 with a photo
    result = api.enroll_face_from_image(1, 'path/to/student_photo.jpg')
    print(f"Result: {result['status']}")
    print(f"Message: {result.get('message', '')}")
    if result['status'] == 'success':
        print(f"Confidence: {result.get('confidence', 0) * 100:.1f}%")
    
    api.close()

def example_2_enroll_from_webcam():
    """Example 2: Enroll a face from webcam"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Enroll Face from Webcam")
    print("="*60)
    
    api = FacialEnrollmentAPI()
    if not api.connect():
        return
    
    # Capture from webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("✗ Cannot open webcam")
        return
    
    print("Press SPACE to capture, any other key to skip")
    
    captured = False
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        cv2.imshow('Press SPACE to capture', frame)
        
        if cv2.waitKey(1) & 0xFF == ord(' '):
            # Enroll with this frame
            result = api.enroll_face_from_array(1, frame)
            print(f"Result: {result['status']}")
            print(f"Message: {result.get('message', '')}")
            if result['status'] == 'success':
                print(f"Confidence: {result.get('confidence', 0) * 100:.1f}%")
            captured = True
            break
        elif cv2.waitKey(1) & 0xFF != 255:  # If any other key
            break
    
    cap.release()
    cv2.destroyAllWindows()
    api.close()

def example_3_check_status():
    """Example 3: Check enrollment status"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Check Enrollment Status")
    print("="*60)
    
    api = FacialEnrollmentAPI()
    if not api.connect():
        return
    
    # Check status for student 1
    status = api.get_enrollment_status(1)
    print(f"Student: {status['name']}")
    print(f"Enrolled: {'✓ YES' if status['enrolled'] else '✗ NO'}")
    print(f"Has Embedding: {'✓ YES' if status['has_embedding'] else '✗ NO'}")
    
    api.close()

def example_4_get_stats():
    """Example 4: Get enrollment statistics"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Get Enrollment Statistics")
    print("="*60)
    
    api = FacialEnrollmentAPI()
    if not api.connect():
        return
    
    stats = api.get_enrollment_stats()
    print(f"Total Students: {stats['total_students']}")
    print(f"Enrolled: {stats['enrolled']}")
    print(f"Pending: {stats['pending']}")
    print(f"Progress: {stats['percentage']:.1f}%")
    
    api.close()

def example_5_train_model():
    """Example 5: Train the model"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Train Facial Recognition Model")
    print("="*60)
    
    api = FacialEnrollmentAPI()
    if not api.connect():
        return
    
    print("Training model... (this may take a minute)")
    result = api.train_model()
    
    print(f"Status: {result['status']}")
    print(f"Faces Processed: {result.get('num_faces', 0)}")
    print(f"Classes: {result.get('classes', 0)}")
    print(f"Message: {result.get('message', '')}")
    
    api.close()

def example_6_list_all_students():
    """Example 6: List all students with enrollment status"""
    print("\n" + "="*60)
    print("EXAMPLE 6: List All Students")
    print("="*60)
    
    api = FacialEnrollmentAPI()
    if not api.connect():
        return
    
    students = api.get_all_students()
    
    print(f"\n{'ID':<5} {'Name':<30} {'Roll Number':<12} {'Status':<15}")
    print("-" * 62)
    
    for student in students:
        status = "✓ Enrolled" if student['enrolled'] else "✗ Pending"
        print(f"{student['student_id']:<5} {student['name']:<30} {student['roll_number']:<12} {status:<15}")
    
    api.close()

def example_7_batch_enroll():
    """Example 7: Batch enroll from a folder"""
    print("\n" + "="*60)
    print("EXAMPLE 7: Batch Enroll from Folder")
    print("="*60)
    
    api = FacialEnrollmentAPI()
    if not api.connect():
        return
    
    # Expected filename format: [student_id]_[name].jpg
    # Example: 1_john_doe.jpg, 2_jane_smith.jpg
    
    image_dir = Path('photos')  # Change to your folder
    
    if not image_dir.exists():
        print(f"✗ Folder not found: {image_dir}")
        return
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    images = [f for f in image_dir.iterdir() if f.suffix.lower() in image_extensions]
    
    print(f"Found {len(images)} images to process\n")
    
    success = 0
    failed = 0
    
    for image_file in images:
        try:
            # Parse student_id from filename
            student_id = int(image_file.stem.split('_')[0])
            print(f"Processing: {image_file.name}...", end=' ')
            
            result = api.enroll_face_from_image(student_id, str(image_file))
            if result['status'] == 'success':
                print(f"✓ Success ({result.get('confidence', 0)*100:.1f}%)")
                success += 1
            else:
                print(f"✗ {result.get('message', 'Failed')}")
                failed += 1
        except Exception as e:
            print(f"✗ Error: {e}")
            failed += 1
    
    print(f"\nResults: {success} success, {failed} failed")
    
    api.close()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("""
╔════════════════════════════════════════════════════════════════╗
║     Facial Enrollment - Programmatic Usage Examples           ║
╚════════════════════════════════════════════════════════════════╝

This script demonstrates how to use the facial enrollment API.

Choose an example to run:
  1. Enroll from Image File
  2. Enroll from Webcam
  3. Check Enrollment Status
  4. Get Statistics
  5. Train Model
  6. List All Students
  7. Batch Enroll from Folder

Run individual examples like:
  python face_enroll_examples.py 1
    """)
    
    import sys
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
        
        if choice == '1':
            example_1_enroll_from_image()
        elif choice == '2':
            example_2_enroll_from_webcam()
        elif choice == '3':
            example_3_check_status()
        elif choice == '4':
            example_4_get_stats()
        elif choice == '5':
            example_5_train_model()
        elif choice == '6':
            example_6_list_all_students()
        elif choice == '7':
            example_7_batch_enroll()
        else:
            print(f"Unknown example: {choice}")
    else:
        print("\nTo run examples, use:")
        print("  python face_enroll_examples.py [number]")
        print("\nExample: python face_enroll_examples.py 4")
