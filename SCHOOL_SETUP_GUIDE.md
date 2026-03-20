# School Attendance Management System Using Facial Recognition

An advanced school-based attendance management system that uses facial recognition technology to automate attendance logging, track student time-in/time-out, and provide real-time notifications to parents/guardians.

## 🎯 Features

### Core Attendance System
- **Real-time Facial Recognition** - Automatic student identification via camera feed
- **Time-In/Time-Out Tracking** - Log entry and exit times automatically
- **Interactive Mode** - Manual selection of entry/exit for verification
- **Early Alert System** - Detect late arrivals and send instant notifications
- **Database Integration** - All data stored in MySQL database

### Parent Notifications
- **SMS Alerts** - Real-time SMS to parent/guardian on student arrival/departure
- **Late Arrival Alerts** - Automatic notification if student arrives after school start time
- **Configuration** - Customizable notification settings via Twilio integration

### Attendance Management
- **Class-wise Tracking** - Track attendance by class/section
- **Student History** - Complete attendance history with timestamps
- **Status Management** - Mark as present, absent, late, or on leave
- **Remarks & Notes** - Add notes to attendance records

### Reporting & Analytics
- **Student Reports** - Individual attendance reports with statistics
- **Class Reports** - Class-level attendance summaries
- **Monthly Statistics** - Attendance trends and patterns
- **PDF Export** - Generate and export reports as PDF
- **CSV Export** - Export data for analysis in spreadsheet applications

### Web Dashboard
- **Interactive Dashboard** - Real-time statistics and quick actions
- **Student Management** - View and manage student records
- **Attendance Logs** - Review daily attendance with filters
- **Report Generation** - Create custom attendance reports
- **Responsive Design** - Mobile-friendly interface

## 📋 System Architecture

```
School Attendance System
│
├── Facial Recognition Module
│   ├── Face Detection (OpenCV DNN)
│   ├── Face Embedding (OpenFace)
│   └── Face Recognition (SVM Classifier)
│
├── Database Layer (MySQL)
│   ├── Students
│   ├── Teachers
│   ├── Classes
│   ├── Attendance Logs
│   ├── Scan Records
│   └── Parent Contacts
│
├── Notification Service
│   ├── SMS Service (Twilio)
│   └── Email Alerts
│
└── Web Interface
    ├── Flask API
    ├── Dashboard
    ├── Reports
    └── Management Console
```

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.7+** - Programming language
- **XAMPP** - For MySQL database (https://www.apachefriends.org)
- **Webcam/USB Camera** - For facial recognition
- **Git** - For version control (optional)

### Step 1: Clone/Download Project
```bash
cd c:\Users\Kaito\Attendance-Management-System-Using-Facial-Recognition
```

### Step 2: Create Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows
source .venv/bin/activate  # On Linux/Mac
```

### Step 3: Run Setup Script
```bash
python setup.py
```

This will:
- Install all Python dependencies
- Create database and tables
- Set up directory structure
- Add sample data (optional)

### Step 4: Manual Database Setup (If needed)
Start XAMPP and run the SQL script:
- Open phpMyAdmin: http://localhost/phpmyadmin
- Import `attendance_db.sql` file
- Create new database: `school_attendance`

### Step 5: Train Facial Recognition Model

**Extract facial embeddings from dataset:**
```bash
python extract_embeddings.py \
    --dataset dataset \
    --embeddings output/embeddings.pickle \
    --detector Models \
    --embedding-model openface_nn4.small2.v1.t7
```

**Train the SVM classifier:**
```bash
python training_model.py \
    --embeddings output/embeddings.pickle \
    --recognizer output/recognizer.pickle \
    --le output/le.pickle
```

## 🚀 Usage

### 1. Real-Time Attendance (CLI - Interactive Mode)
Mark student attendance interactively with face recognition:

```bash
python recognize_video_school.py \
    --detector Models \
    --embedding-model openface_nn4.small2.v1.t7 \
    --recognizer output/recognizer.pickle \
    --le output/le.pickle \
    --mode interactive
```

**How it works:**
1. Opens webcam feed
2. Detects and recognizes student face
3. Displays student name and confidence score
4. Prompts to select: (E)ntry | E(X)it | (F)inish
5. Logs attendance to database
6. Sends SMS notification to parents
7. Checks if student is late and alerts if necessary

### 2. Web Dashboard
Start the Flask web application:

```bash
python app.py
```

Visit: **http://127.0.0.1:5000**

**Dashboard Features:**
- **Dashboard** - Overview of today's attendance
- **Students** - Manage student records
- **Attendance** - View daily/class attendance logs
- **Reports** - Generate attendance reports
  - Filter by date range
  - Export as CSV
  - Export as PDF
  - View statistics

### 3. Real-Time Video Mode (Continuous)
For continuous attendance without interactive prompts:

```bash
python recognize_video_school.py \
    --detector Models \
    --embedding-model openface_nn4.small2.v1.t7 \
    --recognizer output/recognizer.pickle \
    --le output/le.pickle \
    --mode video
```

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# School Information
SCHOOL_INFO = {
    'name': 'Your School Name',
    'school_time_start': '08:00',      # School start time
    'school_time_end': '15:30',        # School end time
    'late_threshold_minutes': 15       # Minutes after start to mark as late
}

# Database Configuration
DATABASE_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',                    # XAMPP default is empty
    'database': 'school_attendance'
}

# SMS Notifications (Twilio)
SMS_CONFIG = {
    'enabled': True,
    'provider': 'twilio',
    'account_sid': 'YOUR_TWILIO_ACCOUNT_SID',
    'auth_token': 'YOUR_TWILIO_AUTH_TOKEN',
    'from_number': '+1234567890'
}

# Recognition Confidence
CONFIDENCE_THRESHOLD = 0.5            # Recognition confidence threshold
FACE_MIN_WIDTH = 20                   # Minimum face width in pixels
FACE_MIN_HEIGHT = 20                  # Minimum face height in pixels
```

## 📱 SMS Notifications Setup (Optional)

To enable parent notifications:

1. **Create Twilio Account:**
   - Visit https://www.twilio.com
   - Sign up for a free account
   - Get your Account SID and Auth Token
   - Get a Twilio phone number

2. **Configure in `config.py`:**
   ```python
   SMS_CONFIG = {
       'enabled': True,
       'account_sid': 'your_account_sid',
       'auth_token': 'your_auth_token',
       'from_number': '+1234567890'
   }
   ```

3. **Add Parent Contacts:**
   - Go to Dashboard → Students
   - Add parent/guardian phone number for each student

4. **Test SMS:**
   - Run recognition system
   - Scan student face
   - Parent should receive SMS notification

## 📊 Database Structure

### Students Table
- `student_id` - Primary key
- `roll_number` - Student roll number
- `first_name` - Student first name
- `last_name` - Student last name
- `class_id` - Class/section
- `face_image_path` - Path to face directory
- `date_of_admission` - Admission date

### Attendance Logs Table
- `log_id` - Primary key
- `student_id` - Foreign key to students
- `date` - Attendance date
- `entry_time` - Time of arrival
- `exit_time` - Time of departure
- `status` - present/absent/late/leave
- `remarks` - Additional notes

### Attendance Scans Table
- `scan_id` - Primary key
- `student_id` - Student ID
- `scan_type` - 'entry' or 'exit'
- `scan_time` - Timestamp of scan
- `confidence_score` - Recognition confidence
- `recognized` - Whether recognition was successful

### Parent Contacts Table
- `contact_id` - Primary key
- `student_id` - Student FK
- `parent_name` - Parent name
- `phone_number` - Contact number
- `relationship` - Parent/Guardian/Other
- `email` - Email address

## 🔍 Troubleshooting

### "Database connection failed"
- Ensure XAMPP MySQL is running
- Check credentials in `config.py`
- Verify database exists in phpMyAdmin

### "Model files not found"
- Ensure `Models/` directory exists
- Download model files from:
  - https://github.com/opencv/opencv_3rdparty

### "No faces detected"
- Ensure adequate lighting
- Position face within 60cm of camera
- Face should be clearly visible

### "Low recognition accuracy"
- Retrain model with more images per student
- Ensure diverse angles and lighting in dataset
- Remove blurry or low-quality images

### SMS not sending
- Verify Twilio configuration
- Check account balance/credits
- Ensure phone numbers have correct format
- Check SMS_CONFIG['enabled'] = True

## 📁 Directory Structure

```
Attendance-Management-System-Using-Facial-Recognition/
├── dataset/                    # Face images by student
│   ├── sameer/
│   ├── manasi/
│   └── ...
├── output/                     # Generated models
│   ├── embeddings.pickle
│   ├── recognizer.pickle
│   └── le.pickle
├── Models/                     # Pretrained models
│   ├── deploy.prototxt
│   └── res10_300x300_ssd_iter_140000.caffemodel
├── templates/                  # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── students.html
│   ├── attendance.html
│   └── reports.html
├── logs/                       # Application logs
├── reports/                    # Generated reports
│
├── app.py                      # Flask web app
├── database.py                 # Database module
├── config.py                   # Configuration
├── notifications.py            # SMS notifications
├── setup.py                    # Setup script
│
├── recognize_video_school.py   # Main attendance system
├── recognize.py                # Single image recognition
├── recognize_video.py          # Legacy video recognition
├── extract_embeddings.py       # Extract face embeddings
├── training_model.py           # Train classifier
├── capture.py                  # Capture face images
│
├── requirements.txt            # Python dependencies
├── attendance_db.sql          # Database schema
└── README.md                   # This file
```

## 🔐 Security Notes

- Change default MySQL password
- Use HTTPS for production deployment
- Keep Twilio credentials secure
- Store sensitive data in environment variables
- Regularly backup database
- Implement user authentication for dashboard

## 📈 Performance Tips

- Limit face embedding batch processing to 50 images
- Optimize camera resolution: 640x480 recommended
- Use GPU acceleration (if available) for faster processing
- Monitor database indexes for query performance
- Archive old attendance records monthly

## 📜 License

This project was developed for educational purposes.

## 👥 Contributors

- Sameer Patel
- Ankita Patil
- Manasi Patil
- Sanskar Shah

## 📞 Support & Documentation

For detailed documentation, API reference, and more examples, refer to:
- `Documentation/` folder
- Individual script docstrings
- Inline code comments

## 🔄 System Update Workflow

To add new students to the system:

1. **Capture Face Images:**
   ```bash
   python capture.py
   ```
   - Creates dataset/{student_name}/ folder
   - Captures 30+ face images from different angles

2. **Add to Database:**
   - Use web dashboard or SQL INSERT
   - Fill student info, class, parent contacts

3. **Retrain Model:**
   ```bash
   python extract_embeddings.py --dataset dataset ...
   python training_model.py --embeddings output/embeddings.pickle ...
   ```

4. **Test Recognition:**
   - Run recognize_video_school.py
   - Test with new student's face

---

**System Ready!** 🎉 

Start with: `python recognize_video_school.py --detector Models --embedding-model openface_nn4.small2.v1.t7 --recognizer output/recognizer.pickle --le output/le.pickle --mode interactive`
