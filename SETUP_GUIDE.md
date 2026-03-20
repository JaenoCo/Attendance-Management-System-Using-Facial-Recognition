# School Attendance System - Complete Setup & Workflow Guide

## Table of Contents
1. [Database Setup](#database-setup)
2. [Application Architecture](#application-architecture)
3. [Attendance Workflows](#attendance-workflows)
4. [Facial Recognition Workflow](#facial-recognition-workflow)
5. [Running the System](#running-the-system)
6. [API Reference](#api-reference)

---

## Database Setup

### Prerequisites
- MySQL Server (XAMPP or standalone)
- Python 3.10+
- Virtual Environment activated

### Step 1: Create Database

The database is automatically created when you run the app. It contains 7 tables:

```
Database: school_attendance

Tables:
├── teachers         (Teacher information)
├── classes          (Class details with teacher assignments)
├── students         (Student records)
├── parent_contacts  (Parent/Guardian phone numbers)
├── attendance_logs  (Daily attendance records - entry/exit times)
├── attendance_scans (Raw facial recognition scans)
└── sms_notifications (SMS alert history)
```

### Step 2: Database Schema

**teachers** table:
```sql
CREATE TABLE teachers (
  teacher_id INT AUTO_INCREMENT PRIMARY KEY,
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  email VARCHAR(100),
  phone VARCHAR(15),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**classes** table:
```sql
CREATE TABLE classes (
  class_id INT AUTO_INCREMENT PRIMARY KEY,
  class_name VARCHAR(100),
  teacher_id INT,
  total_students INT,
  created_at TIMESTAMP,
  FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
);
```

**students** table:
```sql
CREATE TABLE students (
  student_id INT AUTO_INCREMENT PRIMARY KEY,
  roll_number VARCHAR(50),
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  class_id INT,
  date_of_admission DATE,
  face_image_path VARCHAR(255),
  created_at TIMESTAMP,
  FOREIGN KEY (class_id) REFERENCES classes(class_id)
);
```

**parent_contacts** table:
```sql
CREATE TABLE parent_contacts (
  contact_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT,
  parent_name VARCHAR(100),
  relationship VARCHAR(50),
  phone_number VARCHAR(15),
  email VARCHAR(100),
  FOREIGN KEY (student_id) REFERENCES students(student_id)
);
```

**attendance_logs** table:
```sql
CREATE TABLE attendance_logs (
  log_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT,
  date DATE,
  entry_time TIME,
  exit_time TIME,
  status ENUM('present', 'absent', 'late'),
  remarks TEXT,
  FOREIGN KEY (student_id) REFERENCES students(student_id)
);
```

**attendance_scans** table:
```sql
CREATE TABLE attendance_scans (
  scan_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT,
  scan_type ENUM('entry', 'exit'),
  scan_time TIMESTAMP,
  confidence_score FLOAT,
  recognized BOOLEAN,
  FOREIGN KEY (student_id) REFERENCES students(student_id)
);
```

**sms_notifications** table:
```sql
CREATE TABLE sms_notifications (
  notification_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT,
  parent_id INT,
  message TEXT,
  phone_number VARCHAR(15),
  status ENUM('pending', 'sent', 'failed'),
  sent_at TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES students(student_id),
  FOREIGN KEY (parent_id) REFERENCES parent_contacts(contact_id)
);
```

### Step 3: Load Sample Data

Run the FastAPI app - it automatically connects and creates tables:

```bash
python app.py
```

Sample data includes:
- 3 Teachers
- 3 Classes
- 6 Students
- 6 Parent Contacts

---

## Application Architecture

### Project Structure

```
├── app.py                      # FastAPI application (main entry)
├── database.py                 # Database connection layer
├── config.py                   # Configuration settings
├── notifications.py            # SMS notification service
├── recognize_video_school.py   # Real-time facial recognition
├── extract_embeddings.py       # Face embedding extraction
├── training_model.py           # SVM classifier training
│
├── templates/                  # HTML templates
│   ├── base.html               # Base layout
│   ├── dashboard.html          # Dashboard overview
│   ├── students.html           # Student management
│   ├── attendance.html         # Attendance tracking
│   └── reports.html            # Reports & analytics
│
├── Models/                     # Pre-trained models
│   ├── deploy.prototxt         # OpenCV DNN deploy config
│   └── res10_300x300_ssd_iter_140000.caffemodel  # Face detector
│
├── dataset/                    # Student face images
│   ├── sameer/
│   ├── manasi/
│   ├── ankita/
│   ├── sanskar/
│   ├── raj/
│   └── priya/
│
├── output/                     # Trained models (generated)
│   ├── embeddings.pickle       # Face embeddings
│   ├── recognizer.pickle       # SVM classifier
│   └── le.pickle               # Label encoder
│
└── config.py                   # System configuration
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (async web framework) |
| Server | Uvicorn (ASGI server) |
| Database | MySQL 5.7+ |
| Face Detection | OpenCV DNN (SSD) |
| Face Recognition | OpenFace embeddings + SVM |
| Frontend | Bootstrap 5 + jQuery |
| Async Support | aiofiles for file operations |

---

## Attendance Workflows

### Workflow 1: Web Dashboard Attendance

**Path:** Dashboard → Attendance tab

```
1. User clicks "Attendance" in sidebar
   ↓
2. Page loads with today's student list
   ↓
3. GET /api/attendance/today executes
   ↓
4. Database returns all students + their entry/exit times
   ↓
5. Dashboard displays:
   - Roll number
   - Student name
   - Class name
   - Entry time (if marked)
   - Exit time (if marked)
   - Status (present/absent/late)
```

**Key Fields:**
- `student_id` - Unique student identifier
- `date` - Attendance date (TODAY)
- `entry_time` - Time student entered
- `exit_time` - Time student left
- `status` - Attendance status

### Workflow 2: Facial Recognition Attendance

**Path:** Terminal → Real-time scanning

```
1. Run: python recognize_video_school.py --mode interactive
   ↓
2. Camera activates and scans student faces
   ↓
3. Face detected → Extracted as 128-d embedding
   ↓
4. SVM classifier predicts student name
   ↓
5. Display prompt: "[STUDENT_NAME] Detected! E/X/F?"
   E = Entry (arrival)
   X = Exit (departure)
   F = Finish (stop system)
   ↓
6. User presses key (E/X)
   ↓
7. System logs to database:
   - INSERT into attendance_scans (camera detection)
   - UPDATE attendance_logs (entry/exit time)
   ↓
8. If SMS enabled:
   - Send notification to parent
   - "Your child [NAME] marked ENTRY at HH:MM"
```

**Database Operations:**
```python
# 1. Log the facial scan
db.log_attendance_scan(
    student_id=1,
    scan_type='entry',
    confidence_score=0.95
)

# 2. Update attendance log
db.update_or_create_attendance(
    student_id=1,
    scan_type='entry'  # Creates TIME entry
)

# 3. Optional: Send SMS
db.log_sms_notification(
    student_id=1,
    parent_id=1,
    message="Sameer marked ENTRY at 08:30",
    phone_number="+91XXXXXXXXXX"
)
```

---

## Facial Recognition Workflow

### Step 1: Prepare Face Images

Store student face images in `dataset/` folder:

```
dataset/
├── sameer/
│   ├── sameer_001.jpg
│   ├── sameer_002.jpg
│   └── sameer_003.jpg
├── manasi/
│   ├── manasi_001.jpg
│   └── manasi_002.jpg
├── ankita/
│   ├── ankita_001.jpg
│   └── ankita_002.jpg
└── ... (more students)
```

**Requirements:**
- Clear frontal face images
- Good lighting
- 3-5 images per student minimum
- Supported formats: JPG, PNG

### Step 2: Extract Face Embeddings

This converts face images to 128-dimensional vectors:

```bash
python extract_embeddings.py \
  --dataset dataset \
  --embeddings output/embeddings.pickle \
  --detector Models \
  --embedding-model openface_nn4.small2.v1.t7
```

**Output:**
- `output/embeddings.pickle` - Extracted face vectors

**Process:**
```
For each image:
  1. Load image
  2. Detect face using OpenCV DNN
  3. Extract 128-d embedding using OpenFace
  4. Store with student name
```

### Step 3: Train SVM Classifier

This trains a machine learning model to recognize faces:

```bash
python training_model.py \
  --embeddings output/embeddings.pickle \
  --recognizer output/recognizer.pickle \
  --le output/le.pickle
```

**Outputs:**
- `output/recognizer.pickle` - Trained SVM model
- `output/le.pickle` - Label encoder (name mappings)

**What it does:**
```
1. Load embeddings and labels
2. Train SVM classifier
3. Save model for real-time use
```

### Step 4: Run Real-Time Recognition

```bash
python recognize_video_school.py --mode interactive
```

**Real-time Process:**
```
FOR EACH VIDEO FRAME:
  1. Capture frame from camera
  2. Detect faces (OpenCV DNN)
  3. Extract embedding (OpenFace)
  4. Predict name (SVM classifier)
  5. Display on screen
  6. Get user input (E/X/F)
  7. Log to database if E or X
```

---

## Running the System

### Step 1: Activate Virtual Environment

```bash
# Windows
.\.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### Step 2: Start FastAPI Server

```bash
python app.py
```

**Expected Output:**
```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
[INFO] Connected to school_attendance database
[INFO] FastAPI started - Database connection established
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:5000
```

### Step 3: Access Dashboard

**Web Interface:**
- Dashboard: http://127.0.0.1:5000
- API Docs: http://127.0.0.1:5000/docs
- Health Check: http://127.0.0.1:5000/api/health

**Features Available:**
- 📊 Dashboard - Overview statistics
- 👨‍🎓 Students - Manage student records
- ✅ Attendance - Mark/view attendance
- 📈 Reports - Generate attendance reports

### Step 4: (Optional) Run Facial Recognition

In a separate terminal:

```bash
# After training models
python recognize_video_school.py --mode interactive
```

---

## API Reference

### Dashboard Endpoints

#### GET `/api/dashboard-stats`
Returns dashboard statistics.

**Response:**
```json
{
  "total_students": 6,
  "today_present": 4,
  "total_classes": 3
}
```

### Student Endpoints

#### GET `/api/students`
Get all students.

**Response:**
```json
[
  {
    "student_id": 1,
    "roll_number": "001",
    "first_name": "Sameer",
    "last_name": "Patel",
    "class_id": 1,
    "class_name": "Class 10-A",
    "date_of_admission": "2024-01-15"
  }
]
```

#### GET `/api/students/{student_id}`
Get specific student details.

**Response:**
```json
{
  "student_id": 1,
  "roll_number": "001",
  "first_name": "Sameer",
  "last_name": "Patel",
  "class_id": 1
}
```

### Attendance Endpoints

#### GET `/api/attendance/today`
Get today's attendance for all students.

**Response:**
```json
[
  {
    "student_id": 1,
    "roll_number": "001",
    "first_name": "Sameer",
    "last_name": "Patel",
    "class_name": "Class 10-A",
    "entry_time": "08:30:00",
    "exit_time": "15:45:00",
    "status": "present"
  }
]
```

#### GET `/api/attendance/class/{class_id}?date=2024-03-20`
Get class attendance for a specific date.

**Query Parameters:**
- `date` (optional): YYYY-MM-DD format

### Reports Endpoints

#### GET `/api/reports/student-attendance?student_id=1&start_date=2024-03-01&end_date=2024-03-31`
Get student attendance report.

**Query Parameters:**
- `student_id` (required): Student ID
- `start_date` (required): YYYY-MM-DD
- `end_date` (required): YYYY-MM-DD

**Response:**
```json
{
  "attendance": [
    {
      "student_id": 1,
      "date": "2024-03-20",
      "entry_time": "08:30:00",
      "exit_time": "15:45:00",
      "status": "present"
    }
  ],
  "stats": {
    "total_days": 20,
    "present_days": 18,
    "absent_days": 1,
    "late_days": 1,
    "percentage": 90.0
  }
}
```

#### GET `/api/reports/monthly-stats?month=3&year=2024`
Get monthly attendance statistics.

**Query Parameters:**
- `month` (optional): 1-12
- `year` (optional): YYYY

### Other Endpoints

#### GET `/api/classes`
Get all classes with teacher and student count.

#### GET `/api/teachers`
Get all teachers.

#### GET `/api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

## Configuration

Edit `config.py` to customize:

```python
DATABASE_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'school_attendance'
}

FLASK_CONFIG = {
    'secret_key': 'your-secret-key',
    'debug': False
}

SMS_CONFIG = {
    'enabled': False,
    'account_sid': 'YOUR_TWILIO_SID',
    'auth_token': 'YOUR_TWILIO_TOKEN',
    'from_number': '+1XXXXXXXXXX'
}

SCHOOL_INFO = {
    'name': 'School Name',
    'school_time_start': '08:00',
    'late_threshold_minutes': 15
}
```

---

## Troubleshooting

### Database Connection Failed
```
Error: "Unknown database 'school_attendance'"
Solution: Ensure MySQL is running and restart app.py
```

### Face Recognition Not Working
```
Error: "face_recognition module not found"
Solution: Ensure dataset/ has face images and models are trained
```

### Slow API Responses
```
Solution: FastAPI is async, use /docs to test endpoints
or upgrade MySQL to latest version
```

### SMS Not Sending
```
Solution: SMS requires Twilio setup in config.py
Optional feature - system works without it
```

---

## Quick Start Checklist

- [ ] MySQL running (XAMPP or standalone)
- [ ] Virtual environment activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] FastAPI app running: `python app.py`
- [ ] Dashboard accessible: http://127.0.0.1:5000
- [ ] Student face images in `dataset/`
- [ ] Embeddings extracted: `python extract_embeddings.py ...`
- [ ] Models trained: `python training_model.py ...`
- [ ] Real-time recognition running: `python recognize_video_school.py --mode interactive`

---

## Next Steps

1. **Train Facial Recognition Model**
   - Add student face images to `dataset/` folder
   - Run extraction and training scripts
   - Test with `recognize_video_school.py`

2. **Configure SMS Alerts** (Optional)
   - Sign up for Twilio account
   - Add credentials to `config.py`
   - Enable SMS notifications

3. **Deploy to Production**
   - Use production database (e.g., Cloud SQL)
   - Run with Gunicorn: `gunicorn -w 4 -b 0.0.0.0:8000 app:app`
   - Use HTTPS certificates
   - Set up monitoring & logging

4. **Customize for Your School**
   - Add more teachers/classes/students
   - Configure attendance rules
   - Set up holiday calendar
   - Customize SMS messages

---

## Support

For issues or questions:
1. Check Flask logs in terminal
2. Visit API docs: http://127.0.0.1:5000/docs
3. Test health endpoint: http://127.0.0.1:5000/api/health
4. Review database tables using MySQL client
