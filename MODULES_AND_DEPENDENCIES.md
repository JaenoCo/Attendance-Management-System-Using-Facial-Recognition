# Complete Modules, Dependencies & Scripts Guide

## 📦 Installation Command

```bash
pip install -r requirements.txt
```

---

## 🔧 Python Packages Required

### **Computer Vision & Image Processing**
| Package | Version | Purpose |
|---------|---------|---------|
| `opencv-python` | 4.8.1.78 | Face detection, image processing, video feed handling |
| `imutils` | 0.5.4 | Image utilities (VideoStream, resizing, bounding boxes) |
| `numpy` | 2.2.6 | **[LATEST]** Array operations, image data manipulation |
| `Pillow` | 12.1.1 | Image file handling, format conversion |

### **Machine Learning & Data Processing**
| Package | Version | Purpose |
|---------|---------|---------|
| `scikit-learn` | 1.7.2 | **[LATEST]** SVM classifier for face recognition, label encoding |
| `pandas` | 2.0.3 | Data manipulation, CSV handling, attendance reports |

### **Web Framework & Server**
| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.103.1 | Async web framework for REST API endpoints |
| `uvicorn` | 0.23.2 | ASGI server for running FastAPI application |
| `jinja2` | 3.1.2 | HTML template engine for web pages |
| `python-multipart` | 0.0.6 | File upload handling, form data parsing |

### **Authentication & Security**
| Package | Version | Purpose |
|---------|---------|---------|
| `passlib` | 1.7.4 | Password hashing (pbkdf2_sha256 algorithm) |

### **Database**
| Package | Version | Purpose |
|---------|---------|---------|
| `mysql-connector-python` | 8.1.0 | MySQL database connectivity |

### **Background Jobs & Scheduling**
| Package | Version | Purpose |
|---------|---------|---------|
| `APScheduler` | 3.10.4 | **[LATEST]** Daily auto-training scheduler (11 PM cron job) |
| `tzlocal` | 5.3.1 | Timezone handling for scheduler |

### **Notifications (Optional)**
| Package | Version | Purpose |
|---------|---------|---------|
| `twilio` | 8.10.0 | SMS notifications (optional feature) |
| `requests` | 2.31.0 | HTTP requests for API calls |

### **Reporting & PDF (Optional)**
| Package | Version | Purpose |
|---------|---------|---------|
| `reportlab` | 4.0.7 | PDF generation for reports |
| `PyPDF2` | 3.0.1 | PDF manipulation and merging |

### **Utilities**
| Package | Version | Purpose |
|---------|---------|---------|
| `python-dateutil` | 2.8.2 | Date/time parsing and handling |
| `python-dotenv` | 1.0.0 | Loading environment variables from .env files |

### **Mako** (Template Engine - Auto-installed)
| Package | Version | Purpose |
|---------|---------|---------|
| `mako` | 1.3.10 | Template rendering (auto-installed with APScheduler) |
| `MarkupSafe` | 3.0.3 | HTML escaping for templates |

---

## 🐍 Python Version & Virtual Environment

**Required Python Version:** 3.10.10+

**Virtual Environment Setup:**
```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Activate on Linux/Mac
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

---

## 📂 Main Application Scripts

### **1. `app.py` (Main Web Server)**
- **Type:** FastAPI Web Application
- **Purpose:** Core web server with API endpoints, authentication, and web dashboard
- **Dependencies:** 
  - fastapi, uvicorn, jinja2, passlib
  - database.py, facial_recognition.py, config.py
- **Run Command:**
  ```bash
  uvicorn app:app --reload --host 127.0.0.1 --port 5000
  ```
- **Key Features:**
  - User authentication (login/logout)
  - Student management (CRUD operations)
  - Attendance marking & reporting
  - Real-time face recognition endpoint
  - Dashboard with statistics
  - Web templates (HTML forms)

### **2. `database.py` (Database Connection Layer)**
- **Type:** Python Module (Database Helper)
- **Purpose:** MySQL database connection and CRUD operations
- **Dependencies:**
  - mysql.connector, datetime
- **Not Directly Executable** - Used by app.py and scripts
- **Key Methods:**
  - `connect()` - Establish DB connection
  - `disconnect()` - Close connection
  - `get_student_by_id()`
  - `mark_attendance()`
  - `get_class_attendance()` - Get attendance for all students in a class
  - `get_attendance_report()` - Generate attendance reports with date range
  - `get_today_attendance()` - Today's attendance records

### **3. `facial_recognition.py` (Face Recognition Engine)**
- **Type:** Python Module (AI/ML Helper)
- **Purpose:** Face detection, embedding extraction, and recognition using OpenCV
- **Dependencies:**
  - opencv-python, numpy, scikit-learn, pickle, config.py
- **Not Directly Executable** - Used by app.py
- **Key Methods:**
  - `detect_faces()` - Find faces in image
  - `get_face_embedding()` - Extract face embeddings
  - `recognize_face()` - Identify person from face
  - `process_frame()` - Process video frames
  - `capture_face_from_image()` - Extract embeddings from images
  - `train_recognizer()` - Validate recognizer status

### **4. `config.py` (Configuration File)**
- **Type:** Configuration Module
- **Purpose:** Centralized configuration for database, models, thresholds
- **Dependencies:** None (pure Python)
- **Not Directly Executable** - Imported by all modules
- **Configurable Parameters:**
  - Database credentials (host, user, password, database)
  - Face detector path
  - Face embedding model path
  - Recognizer model path
  - Confidence threshold
  - School information
  - Email/SMS configuration

---

## 🤖 Machine Learning & Training Scripts

### **5. `extract_embeddings.py` (Face Embedding Extraction)**
- **Type:** Standalone Script
- **Purpose:** Extract face embeddings from student images in dataset folder
- **Dependencies:**
  - opencv-python, imutils, numpy, pickle
- **Run Command:**
  ```bash
  python extract_embeddings.py \
    --dataset dataset \
    --embeddings output/embeddings.pickle \
    --detector Models \
    --embedding-model openface_nn4.small2.v1.t7 \
    --confidence 0.5
  ```
- **Input:** Student image folders in `dataset/` directory
- **Output:** `output/embeddings.pickle` (serialized embeddings)
- **Command Line Arguments:**
  - `--dataset` - Path to dataset folder with student images
  - `--embeddings` - Output path for embeddings pickle file
  - `--detector` - Path to face detector models
  - `--embedding-model` - Path to OpenFace embedding model
  - `--confidence` - Minimum detection confidence (0.0-1.0)

### **6. `training_model.py` (SVM Model Training)**
- **Type:** Standalone Script
- **Purpose:** Train SVM classifier from face embeddings
- **Dependencies:**
  - scikit-learn, pickle, numpy
- **Run Command:**
  ```bash
  python training_model.py \
    --embeddings output/embeddings.pickle \
    --recognizer output/recognizer.pickle \
    --le output/le.pickle
  ```
- **Input:** `output/embeddings.pickle` (from extract_embeddings.py)
- **Output:** 
  - `output/recognizer.pickle` - Trained SVM model
  - `output/le.pickle` - Label encoder (name mapping)
- **Command Line Arguments:**
  - `--embeddings` - Path to embeddings pickle file
  - `--recognizer` - Output path for trained recognizer model
  - `--le` - Output path for label encoder

### **7. `auto_train.py` (Automated Training Orchestrator)**
- **Type:** Standalone Script
- **Purpose:** Orchestrate automatic daily training (runs via APScheduler at 11 PM)
- **Dependencies:**
  - subprocess, datetime, database.py, config.py
  - Calls: extract_embeddings.py and training_model.py
- **Run Command:**
  ```bash
  python auto_train.py
  ```
- **Automated by:** APScheduler in app.py (scheduled for 11 PM daily)
- **Key Process:**
  1. Extract embeddings from all student faces
  2. Train SVM model on embeddings
  3. Log training session to database
  4. Update student training status
- **Key Methods:**
  - `log_session()` - Log training results to database
  - `extract_embeddings()` - Run extraction subprocess
  - `train_model()` - Run training subprocess
  - `update_student_training_status()` - Update DB with status

---

## 🎥 Video & Recognition Scripts

### **8. `recognize_video.py` (Real-Time Video Face Recognition)**
- **Type:** Standalone Script
- **Purpose:** Real-time face recognition from webcam stream
- **Dependencies:**
  - opencv-python, imutils, numpy, pickle
- **Run Command:**
  ```bash
  python recognize_video.py \
    --detector Models \
    --embedding-model openface_nn4.small2.v1.t7 \
    --recognizer output/recognizer.pickle \
    --le output/le.pickle \
    --confidence 0.5
  ```
- **Input:** Live webcam feed
- **Output:** Display with bounding boxes and name labels
- **Key Features:**
  - Real-time face detection
  - Face recognition with SVM model
  - Bounding box drawing
  - Confidence score display
  - FPS counter
- **Command Line Arguments:**
  - `--detector` - Path to face detector models
  - `--embedding-model` - Path to embedder model
  - `--recognizer` - Path to trained SVM model
  - `--le` - Path to label encoder
  - `--confidence` - Minimum detection confidence

### **9. `recognize.py` (Static Image Recognition)**
- **Type:** Standalone Script (Legacy - not commonly used)
- **Purpose:** Face recognition on static images
- **Dependencies:**
  - opencv-python, imutils, numpy, pickle
- **Similar usage to recognize_video.py but for images**

### **10. `capture.py` (Face Capture Utility)**
- **Type:** Utility Module/Script
- **Purpose:** Capture faces from webcam with error handling
- **Dependencies:**
  - opencv-python, numpy, pickle, config.py
- **Key Features:**
  - Load face detector
  - Load face embedder
  - Load recognizer and label encoder
  - Detect and display faces
  - Error handling for missing models
- **Used by:** App.py for face enrollment

---

## 🗄️ Database & Setup Scripts

### **11. `setup_database.py` (Initial Database Setup)**
- **Type:** Setup Script
- **Purpose:** Create school_attendance database and initialize schema
- **Dependencies:**
  - mysql.connector
- **Run Command (Once Only):**
  ```bash
  python setup_database.py
  ```
- **Output:** Creates database and tables (reads from attendance_db.sql)
- **Required File:** `attendance_db.sql` (SQL schema file)
- **Caution:** Only run once at initial setup

### **12. `migrate_database.py` (Database Migration)**
- **Type:** Migration Script
- **Purpose:** Add missing columns to existing database tables
- **Dependencies:**
  - mysql.connector
- **Run Command:**
  ```bash
  python migrate_database.py
  ```
- **Adds Columns:**
  - `face_training_status` (pending/trained/needs_retrain)
  - `faces_captured` (number of face images)
  - `last_face_capture` (timestamp)
- **Safe:** Checks if columns exist before adding

### **13. `fix_db.py` (Database Repair)**
- **Type:** Maintenance Script
- **Purpose:** Fix database issues and inconsistencies
- **Dependencies:**
  - mysql.connector
- **Run Command:**
  ```bash
  python fix_db.py
  ```
- **Common Uses:**
  - Fix column mismatches
  - Repair corrupted data
  - Reset training status

---

## 📁 Model Files Required

### **Face Detection Models** (in `Models/` folder)
- `deploy.prototxt` - SSD detector architecture
- `res10_300x300_ssd_iter_140000.caffemodel` - SSD detector weights

### **Face Embedding Model** (in root folder)
- `openface_nn4.small2.v1.t7` - OpenFace neural network (96x96 input)

### **Trained Recognition Models** (in `output/` folder - auto-generated)
- `recognizer.pickle` - Trained SVM classifier
- `le.pickle` - Label encoder (maps neural net outputs to student names)
- `embeddings.pickle` - Face embeddings dataset

---

## 📊 Database Schema

### **Tables Created by setup_database.py**

```sql
-- Students Table
students (
    student_id INT PRIMARY KEY,
    roll_number VARCHAR(20) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    class_id INT,
    face_training_status ENUM('pending', 'trained', 'needs_retrain'),
    faces_captured INT,
    last_face_capture TIMESTAMP,
    created_at TIMESTAMP
);

-- Attendance Logs Table
attendance_logs (
    log_id INT PRIMARY KEY,
    student_id INT FOREIGN KEY,
    date DATE,
    entry_time TIME,
    exit_time TIME,
    status ENUM('present', 'absent', 'late', 'leave'),
    created_at TIMESTAMP
);

-- Face Captures Table
face_captures (
    capture_id INT PRIMARY KEY,
    student_id INT FOREIGN KEY,
    image_path VARCHAR(255),
    captured_at TIMESTAMP
);

-- Training Sessions Table
training_sessions (
    session_id INT PRIMARY KEY,
    training_date DATE,
    model_accuracy FLOAT,
    total_faces INT,
    trained_students INT
);

-- Classes/Sections Table (referenced by students)
classes (
    class_id INT PRIMARY KEY,
    class_name VARCHAR(50),
    created_at TIMESTAMP
);
```

---

## 🌐 Web Templates (in `templates/` folder)

| File | Purpose |
|------|---------|
| `login.html` | User authentication page |
| `base.html` | Jinja2 base template (navbar, sidebar) |
| `dashboard.html` | Main dashboard with statistics |
| `students.html` | Student management interface |
| `attendance.html` | Attendance logs viewer |
| `attendance_checkin.html` | Real-time face recognition check-in |
| `reports.html` | Attendance report generation |
| `admin_register.html` | Student registration with face capture |
| `face_enrollment.html` | Dedicated face enrollment page |
| `settings.html` | System settings page |

---

## 📡 REST API Endpoints (from app.py)

### **Authentication**
- `POST /login` - User login
- `GET /logout` - User logout

### **Students**
- `GET /api/students` - List all students
- `POST /api/students` - Create new student
- `PUT /api/students/{id}` - Update student
- `DELETE /api/students/{id}` - Delete student
- `GET /api/students/{id}` - Get student details

### **Attendance**
- `GET /api/attendance/today` - Today's attendance
- `GET /api/attendance/class/{class_id}` - Class attendance
- `POST /api/attendance/checkin` - Mark attendance
- `POST /api/attendance/recognize-face` - Real-time face recognition
- `GET /api/attendance/checkin-status/{scan_id}` - Check scan status

### **Face Operations**
- `POST /api/face/capture` - Capture face from uploaded image
- `POST /api/face/train` - Train recognizer
- `POST /api/face/add-manual` - Add face manually

### **Reports**
- `GET /api/reports/student-attendance` - Student attendance report
- `GET /api/reports/export-csv` - Export attendance as CSV

### **Admin**
- `GET /api/admin/check-connection` - Check database connection
- `POST /api/admin/train-now` - Trigger immediate training

### **Dashboard**
- `GET /api/dashboard-stats` - Dashboard statistics

---

## 🚀 Quick Start Commands

### **1. Initial Setup (One-time)**
```bash
# Create virtual environment
python -m venv .venv

# Activate
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Setup database
python setup_database.py

# Apply migrations
python migrate_database.py
```

### **2. Add Student Images**
```bash
# Create dataset structure
mkdir dataset
mkdir "dataset/Student Name"  # One folder per student

# Add .jpg or .png images of student to their folder
# At least 10-20 images per student recommended
```

### **3. Train Face Recognition Models**
```bash
# Automatic (daily at 11 PM via APScheduler)
# Or manual trigger:
python extract_embeddings.py
python training_model.py
```

### **4. Run Web Server**
```bash
uvicorn app:app --reload --host 127.0.0.1 --port 5000
```

### **5. Access Web Interface**
```
http://127.0.0.1:5000/login
Username: admin
Password: admin123
```

### **6. Test Face Recognition (Optional)**
```bash
python recognize_video.py
```

---

## 🔒 System Security (Default Credentials)

⚠️ **CHANGE THESE IN PRODUCTION:**

| User | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Teacher | `teacher` | `teacher123` |
| Staff | `staff` | `staff123` |

**Database Defaults** (XAMPP)
- User: `root`
- Password: (empty)
- Host: `localhost`

---

## 📋 Dependencies Summary

### **Core System**
- Python 3.10.10+
- MySQL (via XAMPP)
- Virtual Environment (.venv)

### **Web Framework**
- FastAPI + Uvicorn
- Jinja2 Templates
- Passlib Authentication

### **Computer Vision & ML**
- OpenCV 4.8.1.78
- NumPy 2.2.6 (Latest compatible)
- scikit-learn 1.7.2 (Latest SVM library)
- imutils (Video streaming utilities)

### **Database**
- MySQL Connector 8.1.0

### **Background Jobs**
- APScheduler 3.10.4 (Daily training at 11 PM)
- tzlocal 5.3.1 (Timezone support)

### **Optional Features**
- Twilio (SMS notifications)
- ReportLab (PDF generation)
- python-dotenv (Environment variables)

---

## ✅ Verification Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] All packages from requirements.txt installed
- [ ] MySQL running (XAMPP)
- [ ] Database initialized with setup_database.py
- [ ] Student dataset folder created
- [ ] Model files exist in Models/ folder
- [ ] Web server starts without errors
- [ ] Can access http://127.0.0.1:5000/login
- [ ] Face detection working (recognizer trained)

---

**Last Updated:** March 22, 2026  
**System Version:** 2.0  
**Python Version:** 3.10.10+  
**Primary Dependencies:** FastAPI, OpenCV, scikit-learn, MySQL, APScheduler
