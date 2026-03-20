# Python Facial Enrollment - Complete Usage Guide

## Overview

You now have **two ways** to enroll faces for your students:

1. **Web Interface** (http://127.0.0.1:5000/face-enrollment) - Graphical UI
2. **Python Scripts** (Command-line + Programmatic API) - Automated enrollment

This guide covers the Python scripts approach, which is perfect for:
- Batch enrollment of many students
- Automation in other Python applications
- Scripted enrollment workflows
- Integration with other systems

---

## 🚀 Quick Start

### Method 1: Command-Line Interface (Easy)

**Enroll a face from an image:**
```bash
python face_enroll_cli.py capture-image --student_id 1 --image path/to/photo.jpg
```

**Enroll a face from webcam:**
```bash
python face_enroll_cli.py capture-webcam --student_id 1
```

**Train the model:**
```bash
python face_enroll_cli.py train
```

**See all students:**
```bash
python face_enroll_cli.py list
```

---

## 📖 Complete Command Reference

### `list` - List All Students

**Description:** Display all students and their enrollment status

**Syntax:**
```bash
python face_enroll_cli.py list
```

**Output:**
```
================================================================================
ID    Roll         Name                               Face Enrolled
================================================================================
1     001          John Doe                           ✓ YES
2     002          Jane Smith                         ✗ NO
3     003          Alex Kumar                         ✓ YES
================================================================================
```

---

### `status` - Check Enrollment Status

**Description:** Check if a specific student has a face enrolled

**Syntax:**
```bash
python face_enroll_cli.py status --student_id <ID>
```

**Example:**
```bash
python face_enroll_cli.py status --student_id 1
```

**Output:**
```
==================================================
Student: John Doe
ID: 1
Roll Number: 001
Status: ✓ ENROLLED
Has Embedding: ✓ YES
==================================================
```

---

### `capture-image` - Enroll from Image

**Description:** Capture and enroll a face from an image file

**Syntax:**
```bash
python face_enroll_cli.py capture-image --student_id <ID> --image <PATH>
```

**Example:**
```bash
python face_enroll_cli.py capture-image --student_id 1 --image photos/john.jpg
```

**Output:**
```
[*] Processing face for John Doe...
[✓] Face captured successfully
[✓] Confidence: 97.8%
[✓] Database updated
[✓] Image saved to: dataset/John Doe/
```

**Supported Formats:** JPG, PNG, BMP

**Tips:**
- Image should have clear, visible face
- Well-lit photos work best
- Face should fill 60-80% of image

---

### `capture-webcam` - Enroll from Webcam

**Description:** Capture face using connected webcam

**Syntax:**
```bash
python face_enroll_cli.py capture-webcam --student_id <ID>
```

**Example:**
```bash
python face_enroll_cli.py capture-webcam --student_id 1
```

**Controls:**
- SPACE = Capture current frame
- Q = Quit without capturing

**Output:**
```
[*] Capturing face for John Doe from webcam...
[*] Opening webcam... (Press SPACE to capture, Q to quit)
[*] Image captured!
[*] Processing face...
[✓] Face captured successfully
[✓] Confidence: 98.5%
[✓] Database updated
[✓] Image saved to: dataset/John Doe/
```

---

### `train` - Train Facial Model

**Description:** Train the facial recognition model using all enrolled faces

**Syntax:**
```bash
python face_enroll_cli.py train
```

**Output:**
```
[*] Starting model training...
[✓] Model trained successfully!
[✓] Faces processed: 15
[✓] Student classes: 15
[✓] Models saved to output/
```

**Tips:**
- Takes 15-30 seconds for 50+ faces
- Need at least 3 enrolled faces
- More faces = better accuracy
- Train after enrolling batches of students

---

### `stats` - View Statistics

**Description:** Show enrollment statistics

**Syntax:**
```bash
python face_enroll_cli.py stats
```

**Output:**
```
============================================================
ENROLLMENT STATISTICS
============================================================
Total Students:    100
Enrolled:          25
Pending:           75
Progress:          25.0%
Progress Bar:      [██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░]
============================================================
```

---

### `batch-enroll` - Batch Enroll from Folder

**Description:** Enroll multiple students from a folder of images

**Syntax:**
```bash
python face_enroll_cli.py batch-enroll --folder <PATH>
```

**Example:**
```bash
python face_enroll_cli.py batch-enroll --folder ./photos/
```

**Filename Format Required:**
```
[student_id]_[name].jpg
```

**Examples:**
```
1_john_doe.jpg
2_jane_smith.jpg
3_alex_kumar.jpg
```

**Output:**
```
[*] Found 10 images to process

[1/10] Processing: 1_john_doe.jpg
[✓] Face captured successfully
[✓] Confidence: 97.8%
[✓] Database updated
[✓] Image saved to: dataset/John Doe/

[2/10] Processing: 2_jane_smith.jpg
[✓] Face captured successfully
...

==================================================
Batch Enrollment Complete
==================================================
Success: 9
Failed: 1
Total: 10
==================================================
```

**Tips:**
- Place all images in one folder
- Use correct filename format: `[id]_[name].jpg`
- Works with JPG, PNG, BMP
- Automatically skips files that don't match format

---

## 💻 Programmatic API (For Developers)

If you want to use facial enrollment in your own Python code:

### Basic Template

```python
from face_enroll_examples import FacialEnrollmentAPI

# Create API instance
api = FacialEnrollmentAPI()

# Connect to database
if not api.connect():
    print("Failed to connect")
    exit()

# Do something with the API
# ... (see examples below)

# Always close connection
api.close()
```

---

### Example 1: Enroll from Image

```python
from face_enroll_examples import FacialEnrollmentAPI

api = FacialEnrollmentAPI()
api.connect()

result = api.enroll_face_from_image(1, 'path/to/photo.jpg')

print(f"Status: {result['status']}")
print(f"Message: {result.get('message', '')}")
if result['status'] == 'success':
    print(f"Confidence: {result['confidence'] * 100:.1f}%")

api.close()
```

---

### Example 2: Enroll from Webcam

```python
from face_enroll_examples import FacialEnrollmentAPI
import cv2

api = FacialEnrollmentAPI()
api.connect()

# Capture from webcam
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

# Enroll the captured frame
result = api.enroll_face_from_array(1, frame)

print(f"Status: {result['status']}")
print(f"Message: {result.get('message', '')}")

api.close()
```

---

### Example 3: Check Enrollment Status

```python
from face_enroll_examples import FacialEnrollmentAPI

api = FacialEnrollmentAPI()
api.connect()

status = api.get_enrollment_status(1)

print(f"Student: {status['name']}")
print(f"Enrolled: {status['enrolled']}")
print(f"Has Embedding: {status['has_embedding']}")

api.close()
```

---

### Example 4: Get Statistics

```python
from face_enroll_examples import FacialEnrollmentAPI

api = FacialEnrollmentAPI()
api.connect()

stats = api.get_enrollment_stats()

print(f"Total: {stats['total_students']}")
print(f"Enrolled: {stats['enrolled']}")
print(f"Pending: {stats['pending']}")
print(f"Progress: {stats['percentage']:.1f}%")

api.close()
```

---

### Example 5: Train Model

```python
from face_enroll_examples import FacialEnrollmentAPI

api = FacialEnrollmentAPI()
api.connect()

result = api.train_model()

print(f"Status: {result['status']}")
print(f"Faces: {result['num_faces']}")
print(f"Classes: {result['classes']}")

api.close()
```

---

### Example 6: List All Students

```python
from face_enroll_examples import FacialEnrollmentAPI

api = FacialEnrollmentAPI()
api.connect()

students = api.get_all_students()

for student in students:
    status = "Enrolled" if student['enrolled'] else "Pending"
    print(f"{student['name']}: {status}")

api.close()
```

---

### Example 7: Complete Batch Workflow

```python
from face_enroll_examples import FacialEnrollmentAPI
from pathlib import Path

api = FacialEnrollmentAPI()
api.connect()

# Get all images in a folder
image_dir = Path('photos')
images = list(image_dir.glob('*.jpg'))

print(f"Enrolling {len(images)} students...")

for image_file in images:
    # Parse student ID from filename
    student_id = int(image_file.stem.split('_')[0])
    
    # Enroll
    result = api.enroll_face_from_image(student_id, str(image_file))
    
    if result['status'] == 'success':
        print(f"✓ {image_file.name}: {result['confidence']*100:.1f}%")
    else:
        print(f"✗ {image_file.name}: {result.get('message', 'Failed')}")

# Train after all enrollment
print("\nTraining model...")
train_result = api.train_model()
print(f"✓ Model trained on {train_result['num_faces']} faces")

api.close()
```

---

## 📋 Real-World Workflow Examples

### Workflow 1: Enroll 20 Students in 30 Minutes

**Step 1: Prepare photos**
```
Create folder: photos/
File naming: 1_john_doe.jpg, 2_jane_smith.jpg, etc.
```

**Step 2: Run batch enrollment**
```bash
python face_enroll_cli.py batch-enroll --folder ./photos/
```

**Step 3: Check progress**
```bash
python face_enroll_cli.py stats
```

**Step 4: Train model**
```bash
python face_enroll_cli.py train
```

**Done!** System ready for attendance.

---

### Workflow 2: Enroll Each Day

**Monday (10 students):**
```bash
python face_enroll_cli.py batch-enroll --folder ./monday_batch/
python face_enroll_cli.py train
```

**Tuesday (10 more students):**
```bash
python face_enroll_cli.py batch-enroll --folder ./tuesday_batch/
python face_enroll_cli.py train
```

**Wednesday (final students):**
```bash
python face_enroll_cli.py batch-enroll --folder ./wednesday_batch/
python face_enroll_cli.py train
```

**Result:** All students enrolled, model trained on 30 faces.

---

### Workflow 3: Selective Enrollment

**Check who needs face:**
```bash
python face_enroll_cli.py list
```

**Enroll specific student:**
```bash
python face_enroll_cli.py capture-webcam --student_id 5
```

**Retrain model:**
```bash
python face_enroll_cli.py train
```

---

## 🎯 Practical Use Cases

### Use Case 1: Staff Entry

```python
from face_enroll_examples import FacialEnrollmentAPI
import cv2

# Admin enrolls new staff member
api = FacialEnrollmentAPI()
api.connect()

print("Activating webcam for staff enrollment...")
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

# Enroll staff with ID 101
result = api.enroll_face_from_array(101, frame)
print(f"Staff enrolled: {result['message']}")

# Retrain model
api.train_model()
print("System ready with updated staff")

api.close()
```

---

### Use Case 2: Visitor Registration

```python
from face_enroll_examples import FacialEnrollmentAPI
import cv2
import datetime

api = FacialEnrollmentAPI()
api.connect()

# Create visitor entry
visitor_id = 9001  # Visitor ID
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Capture visitor face
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

# Save photo
cv2.imwrite(f'visitors/visitor_{timestamp}.jpg', frame)

# Enroll visitor
result = api.enroll_face_from_array(visitor_id, frame)
print(f"Visitor registered: {result['message']}")

api.close()
```

---

### Use Case 3: Class Photo Collection

```python
from face_enroll_examples import FacialEnrollmentAPI
from pathlib import Path

api = FacialEnrollmentAPI()
api.connect()

# Enroll Class 10-A students
class_photos = Path('Class_10A')

success = 0
for photo in class_photos.glob('*.jpg'):
    student_id = int(photo.stem.split('_')[0])
    result = api.enroll_face_from_image(student_id, str(photo))
    if result['status'] == 'success':
        success += 1

print(f"Enrolled {success} students from Class 10-A")

# Retrain
api.train_model()

api.close()
```

---

## ⚠️ Troubleshooting

### Issue: "No face detected"

**Cause:** Face not visible or poor lighting

**Solution:**
```bash
# Try again with better lighting
# Ensure face fills 60-80% of image
# Try webcam instead of image file
python face_enroll_cli.py capture-webcam --student_id 1
```

---

### Issue: "Student not found"

**Cause:** Invalid student ID

**Solution:**
```bash
# First, list all students
python face_enroll_cli.py list

# Use a valid ID from the list
python face_enroll_cli.py capture-image --student_id 1 --image photo.jpg
```

---

### Issue: "Database connection error"

**Cause:** MySQL not running or wrong credentials

**Solution:**
```bash
# Check MySQL is running
# Edit DB_CONFIG in the script if needed:
# DB_CONFIG = {
#     'host': 'localhost',
#     'user': 'root',
#     'password': 'root',
#     'database': 'school_attendance'
# }
```

---

### Issue: "Cannot find image file"

**Cause:** Wrong file path

**Solution:**
```bash
# Use absolute path
python face_enroll_cli.py capture-image --student_id 1 --image "C:\path\to\photo.jpg"

# Or relative path from project folder
python face_enroll_cli.py capture-image --student_id 1 --image "photos\photo.jpg"
```

---

### Issue: "Webcam not working"

**Cause:** Camera not found or in use

**Solution:**
```bash
# Try image upload instead
python face_enroll_cli.py capture-image --student_id 1 --image photo.jpg

# Or check if webcam is being used by another app
# Close other programs and try again
```

---

## 🚀 Advanced Usage

### Batch Processing with Error Handling

```python
from face_enroll_examples import FacialEnrollmentAPI
from pathlib import Path

def batch_enroll_with_logging(folder_path, log_file='enrollment_log.txt'):
    """Enroll students with detailed logging"""
    
    api = FacialEnrollmentAPI()
    api.connect()
    
    with open(log_file, 'w') as log:
        images = list(Path(folder_path).glob('*.jpg'))
        
        for image_file in images:
            try:
                student_id = int(image_file.stem.split('_')[0])
                result = api.enroll_face_from_image(student_id, str(image_file))
                
                status = result['status']
                confidence = result.get('confidence', 0) * 100
                message = result.get('message', '')
                
                log_entry = f"{image_file.name}: {status} ({confidence:.1f}%) - {message}\n"
                log.write(log_entry)
                
            except Exception as e:
                log.write(f"{image_file.name}: ERROR - {str(e)}\n")
    
    # Train after all
    result = api.train_model()
    print(f"Training complete: {result['num_faces']} faces processed")
    
    api.close()
    print(f"Log saved to {log_file}")

# Run it
batch_enroll_with_logging('./photos/', 'enrollment_report.txt')
```

---

### Automated Daily Enrollment

```python
# enrollment_scheduler.py

from face_enroll_examples import FacialEnrollmentAPI
import schedule
import time
from datetime import datetime

def daily_enrollment_job():
    """Run enrollment every morning at 9 AM"""
    
    api = FacialEnrollmentAPI()
    api.connect()
    
    # Check current statistics
    stats = api.get_enrollment_stats()
    
    # Log to file
    with open('enrollment_log.txt', 'a') as f:
        f.write(f"\n{datetime.now()}: Current Status\n")
        f.write(f"  Total: {stats['total_students']}\n")
        f.write(f"  Enrolled: {stats['enrolled']}\n")
        f.write(f"  Pending: {stats['pending']}\n")
        f.write(f"  Progress: {stats['percentage']:.1f}%\n")
    
    # If less than 80% enrolled, send notification
    if stats['percentage'] < 80:
        print(f"[!] Only {stats['percentage']:.1f}% enrolled!")
        # Could send email, SMS, etc.
    
    api.close()

# Schedule to run daily at 9 AM
schedule.every().day.at("09:00").do(daily_enrollment_job)

# Keep running
while True:
    schedule.run_pending()
    time.sleep(60)

# Run with: python enrollment_scheduler.py
```

---

## 📊 Performance Tips

### Enroll Faster
1. **Use batch enroll:** 10x faster than individual enrollments
2. **Good lighting:** Reduces processing errors
3. **Clear faces:** Front-facing, no accessories
4. **Stop background apps:** More CPU available

### Optimize Accuracy
1. **Multiple samples:** Enroll 3-5 photos per student
2. **Variety:** Different angles, lighting conditions
3. **Clean data:** Discard blurry/poor quality photos
4. **Regular training:** Retrain model after each batch

---

## 📁 File Structure

After using these scripts, you'll have:

```
project_root/
├── face_enroll_cli.py               ← Command-line tool
├── face_enroll_examples.py          ← Python API
├── facial_recognition.py            ← Core module (existing)
├── dataset/
│   ├── John Doe/
│   │   ├── face_001_2024-03-20.png
│   │   └── face_002_2024-03-20.png
│   └── Jane Smith/
│       └── face_001_2024-03-20.png
├── output/
│   ├── recognizer.pickle            ← Trained model
│   └── le.pickle                    ← Label encoder
└── photos/                          ← Your batch images
    ├── 1_john_doe.jpg
    └── 2_jane_smith.jpg
```

---

## ✅ Checklist

Before using these scripts:

- [ ] Python virtual environment activated
- [ ] MySQL running and database connected
- [ ] facial_recognition.py exists and loads models
- [ ] Database has `student_id`, `face_registered`, `face_data` columns
- [ ] Webcam works (if using capture-webcam)
- [ ] Image files ready (if using batch-enroll)

---

## 🔗 Quick Links

- **Command-line tool:** `face_enroll_cli.py`
- **Python API:** Import `FacialEnrollmentAPI` from `face_enroll_examples.py`
- **Core module:** `facial_recognition.py`
- **Web interface:** http://127.0.0.1:5000/face-enrollment

---

## 💡 Pro Tips

1. **Always train after enrollment:** `python face_enroll_cli.py train`
2. **Check status regularly:** `python face_enroll_cli.py stats`
3. **Use batch-enroll for many students:** Much faster!
4. **Keep photos organized:** Use consistent naming `[id]_[name].jpg`
5. **Test with a small group first:** Before full deployment

---

**Status: Ready to Use** ✅

You now have complete programmatic access to facial enrollment!
