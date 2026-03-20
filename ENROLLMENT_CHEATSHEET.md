# 🚀 Facial Enrollment - Quick Reference Card

## Command-Line Quick Reference

```bash
# List all students
python face_enroll_cli.py list

# Check enrollment status
python face_enroll_cli.py status --student_id 1

# Enroll from image
python face_enroll_cli.py capture-image --student_id 1 --image photo.jpg

# Enroll from webcam (Press SPACE to capture, Q to quit)
python face_enroll_cli.py capture-webcam --student_id 1

# Train facial model
python face_enroll_cli.py train

# Show statistics
python face_enroll_cli.py stats

# Batch enroll from folder (files: 1_name.jpg, 2_name.jpg, etc.)
python face_enroll_cli.py batch-enroll --folder ./photos/
```

---

## Python API Quick Reference

### Import
```python
from face_enroll_examples import FacialEnrollmentAPI

api = FacialEnrollmentAPI()
api.connect()
# ... do something ...
api.close()
```

### Methods
```python
# Enroll from image
api.enroll_face_from_image(student_id, image_path)

# Enroll from numpy array
api.enroll_face_from_array(student_id, image_array)

# Check status
api.get_enrollment_status(student_id)

# Get all students
api.get_all_students()

# Get statistics
api.get_enrollment_stats()

# Train model
api.train_model()
```

---

## Typical Workflow

```bash
# 1. Prepare photos in folder (name: 1_john.jpg, 2_jane.jpg, etc.)
mkdir photos

# 2. Batch enroll
python face_enroll_cli.py batch-enroll --folder ./photos/

# 3. Check progress
python face_enroll_cli.py stats

# 4. Train model
python face_enroll_cli.py train

# 5. Done! Ready for attendance
```

---

## Common Tasks

### Enroll Single Student (Quickest)
```bash
python face_enroll_cli.py capture-webcam --student_id 1
```

### Enroll Multiple Students (Fastest)
```bash
python face_enroll_cli.py batch-enroll --folder ./class_photos/
```

### Retrain Model
```bash
python face_enroll_cli.py train
```

### Check Who's Not Enrolled
```bash
python face_enroll_cli.py list
# Look for "✗ NO" in Face Enrolled column
```

### Get Current Progress
```bash
python face_enroll_cli.py stats
```

---

## Python Integration Examples

### In 3 Lines
```python
from face_enroll_examples import FacialEnrollmentAPI
api = FacialEnrollmentAPI()
api.connect()
api.enroll_face_from_image(1, 'photo.jpg')
api.close()
```

### Batch with Loop
```python
from face_enroll_examples import FacialEnrollmentAPI
from pathlib import Path

api = FacialEnrollmentAPI()
api.connect()

for image in Path('photos').glob('*.jpg'):
    student_id = int(image.stem.split('_')[0])
    api.enroll_face_from_image(student_id, str(image))

api.train_model()
api.close()
```

### With Webcam
```python
from face_enroll_examples import FacialEnrollmentAPI
import cv2

api = FacialEnrollmentAPI()
api.connect()

cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

api.enroll_face_from_array(1, frame)
api.train_model()
api.close()
```

---

## Results

### Success Response
```
[✓] Face captured successfully
[✓] Confidence: 98.5%
[✓] Database updated
[✓] Image saved to: dataset/John Doe/
```

### Training Response
```
[✓] Model trained successfully!
[✓] Faces processed: 15
[✓] Student classes: 15
[✓] Models saved to output/
```

### Progress Response
```
Total Students: 100
Enrolled: 25
Pending: 75
Progress: 25.0%
```

---

## Keyboard Controls

### Webcam Capture
- **SPACE** = Capture frame
- **Q** = Quit without capturing

---

## File Naming for Batch

```
Format: [student_id]_[anything].jpg

Examples:
1_john_doe.jpg
2_jane_smith.jpg
3_alex_kumar.jpg
```

---

## Debug Commands

```bash
# List students (see all IDs)
python face_enroll_cli.py list

# Check specific student
python face_enroll_cli.py status --student_id 1

# Show all stats
python face_enroll_cli.py stats

# Test image enrollment
python face_enroll_cli.py capture-image --student_id 1 --image test.jpg
```

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Student not found` | Run `list` to see valid IDs |
| `No face detected` | Better lighting, centered face |
| `Image file not found` | Check file path and extension |
| `Database connection error` | Ensure MySQL is running |
| `Webcam not working` | Accept camera permission, try image upload |

---

## Timing Guide

| Task | Time |
|------|------|
| Enroll 1 student (image) | 2 seconds |
| Enroll 1 student (webcam) | 5 seconds |
| Batch enroll 10 students | 3-5 minutes |
| Batch enroll 50 students | 15-20 minutes |
| Train model (10 faces) | 5 seconds |
| Train model (50 faces) | 20 seconds |
| Train model (100+ faces) | 30 seconds |

---

## System Info

**Primary Tools:**
- `face_enroll_cli.py` - Command-line interface
- `face_enroll_examples.py` - Python API
- `facial_recognition.py` - Core engine

**Database:** MySQL (school_attendance)  
**Languages:** Python, SQL

**Output Location:** `./output/` (trained models)  
**Image Storage:** `./dataset/` (student face images)

---

## Pro Tips

```
✓ Always train after enrolling multiple students
✓ Use batch-enroll for 10+ students (much faster!)
✓ Use webcam for individual students
✓ Check stats before training
✓ Ensure good lighting when capturing
✓ Keep photos in [id]_[name].jpg format
✓ Train model once enrollment reaches 80%+
```

---

## Status Indicators

```
✓ = Success / YES / Ready
✗ = Failed / NO / Not Ready
[*] = Processing / In Progress
[!] = Warning / Note
[✓] = Complete / Done
```

---

**Ready to use!** Pick a command above and run it! 🎯
