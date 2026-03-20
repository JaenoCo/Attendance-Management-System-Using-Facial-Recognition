# ⚡ Quick Start Guide - School Attendance System

## What's New? 🎉

Your attendance system has been completely redesigned for **school-based operations** with:

✅ **MySQL Database** - Store all student and attendance data  
✅ **Web Dashboard** - Beautiful interface for management  
✅ **Real-time Tracking** - Entry/Exit time logging  
✅ **Parent Notifications** - SMS alerts via Twilio  
✅ **Attendance Reports** - Daily, monthly, and detailed analytics  
✅ **Class Management** - Track attendance by class/section  
✅ **Interactive Mode** - Manual entry/exit selection for verification  

---

## 🚀 Getting Started (5 Minutes)

### 1️⃣ Start XAMPP MySQL
- Open XAMPP Control Panel
- Click **Start** next to MySQL
- Wait until it shows "Running"

### 2️⃣ Create Database
Since you're already in a Python virtual environment:

```bash
# Import the database schema
# Option A: Via Python
python -c "
import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='')
cursor = conn.cursor()
with open('attendance_db.sql', 'r') as f:
    for stmt in f.read().split(';'):
        if stmt.strip():
            cursor.execute(stmt)
conn.commit()
conn.close()
print('Database created successfully!')
"
```

Or **Option B**: Via phpMyAdmin
- Go to http://localhost/phpmyadmin
- Import `attendance_db.sql` file

### 3️⃣ Add Students to Database

Open MySQL command line or phpMyAdmin and run:

```sql
-- Add sample students
INSERT INTO students (roll_number, first_name, last_name, class_id, date_of_admission) VALUES
('001', 'Sameer', 'Patel', 1, '2024-01-15'),
('002', 'Manasi', 'Patil', 1, '2024-01-15'),
('003', 'Ankita', 'Patil', 2, '2024-01-15'),
('004', 'Sanskar', 'Shah', 2, '2024-01-15');

-- Add parent contacts
INSERT INTO parent_contacts (student_id, parent_name, phone_number, relationship, email) VALUES
(1, 'Rajesh Patel', '9876543210', 'Father', 'rajesh@email.com'),
(2, 'Priya Patil', '9876543211', 'Mother', 'priya@email.com'),
(3, 'Vikram Patil', '9876543212', 'Father', 'vikram@email.com'),
(4, 'Aisha Shah', '9876543213', 'Mother', 'aisha@email.com');

-- Add classes and teachers
INSERT INTO teachers (employee_id, first_name, last_name, email, phone) VALUES
('EMP001', 'Rajesh', 'Kumar', 'rajesh@school.edu', '9876543220'),
('EMP002', 'Priya', 'Singh', 'priya@school.edu', '9876543221');

INSERT INTO classes (class_name, teacher_id) VALUES
('Class A', 1),
('Class B', 2);
```

### 4️⃣ Train Facial Recognition Model

First, ensure you have student faces in `dataset/sameer/`, `dataset/manasi/`, etc.

```bash
# Extract facial embeddings
python extract_embeddings.py \
    --dataset dataset \
    --embeddings output/embeddings.pickle \
    --detector Models \
    --embedding-model openface_nn4.small2.v1.t7

# Train the classifier
python training_model.py \
    --embeddings output/embeddings.pickle \
    --recognizer output/recognizer.pickle \
    --le output/le.pickle
```

### 5️⃣ Start Attendance System (Interactive Mode)

```bash
python recognize_video_school.py \
    --detector Models \
    --embedding-model openface_nn4.small2.v1.t7 \
    --recognizer output/recognizer.pickle \
    --le output/le.pickle \
    --mode interactive
```

**How to use:**
1. Look at the webcam
2. System detects and recognizes your face
3. Shows: "RECOGNIZED: Name (Confidence: XX%)"
4. Press:
   - **E** = Entry (Mark in-time)
   - **X** = Exit (Mark out-time)
   - **F** = Finish (Quit)
5. SMS sent automatically to parent!

### 6️⃣ Open Web Dashboard

In another terminal (keep attendance system running):

```bash
python app.py
```

Then open: **http://127.0.0.1:5000**

**Dashboard sections:**
- 📊 **Dashboard** - Today's attendance overview
- 👥 **Students** - Student list and details
- ✅ **Attendance** - Daily attendance logs with filters
- 📋 **Reports** - Detailed reports, exports, analytics

---

## 📊 What Gets Logged?

Every scan creates records in these tables:

### `attendance_scans` (Raw scans)
| scan_id | student_id | scan_type | scan_time | confidence_score |
|---------|-----------|-----------|-----------|------------------|
| 1 | 1 | entry | 2024-03-20 08:15:30 | 0.92 |
| 2 | 1 | exit | 2024-03-20 15:45:20 | 0.95 |

### `attendance_logs` (Summary)
| log_id | student_id | date | entry_time | exit_time | status |
|--------|-----------|------|-----------|----------|--------|
| 1 | 1 | 2024-03-20 | 08:15:30 | 15:45:20 | present |

### `sms_notifications` (Parent alerts)
| notification_id | student_id | message | phone_number | status | sent_at |
|-----------------|-----------|---------|--------------|--------|---------|
| 1 | 1 | Student arrived at 08:15 | 9876543210 | sent | 2024-03-20 08:15:35 |

---

## 🔧 Configuration

### School Hours & Late Threshold
Edit `config.py`:

```python
SCHOOL_INFO = {
    'name': 'Your School Name',
    'school_time_start': '08:00',      # When school starts
    'school_time_end': '15:30',        # When school ends
    'late_threshold_minutes': 15       # Minutes after start to mark late
}
```

### Database Credentials
```python
DATABASE_CONFIG = {
    'host': 'localhost',               # XAMPP MySQL host
    'user': 'root',                    # XAMPP default user
    'password': '',                    # XAMPP default (empty)
    'database': 'school_attendance'
}
```

### SMS Notifications (Optional)

To enable SMS alerts to parents:

1. **Get Twilio Account:**
   - Go to https://www.twilio.com
   - Sign up (free trial with $15 credit)
   - Get: Account SID, Auth Token, Phone Number

2. **Update `config.py`:**
   ```python
   SMS_CONFIG = {
       'enabled': True,
       'account_sid': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
       'auth_token': 'your_auth_token_here',
       'from_number': '+1234567890'  # Your Twilio number
   }
   ```

3. **Test:** Run system and scan a student's face. Parent gets SMS!

---

## 📈 Viewing Reports

### Via Web Dashboard:
1. Go to **Reports** section
2. Select a student
3. Choose date range
4. Click **Generate Report**

**You can:**
- View attendance by date
- See entry/exit times
- View status (present/absent/late)
- Export as CSV (spreadsheet)
- Print report

### Sample Report Output:
```
Student: Sameer Patel (Roll: 001)
Period: 01-Mar-2024 to 31-Mar-2024

Attendance Summary:
- Total Working Days: 22
- Days Present: 21
- Days Absent: 1
- Days Late: 0
- Attendance Percentage: 95.45%

Detailed Log:
Date       | Entry Time | Exit Time | Status  | Remarks
-----------|------------|-----------|---------|----------
01-Mar-24  | 08:15      | 15:45     | Present | -
02-Mar-24  | 08:05      | 15:30     | Present | -
03-Mar-24  | -          | -         | Absent  | Medical Leave
...
```

---

## 🆚 Interactive vs Video Mode

| Aspect | **Interactive Mode** | **Video Mode** |
|--------|-------------------|------------|
| Use Case | Manual verification | Hands-free monitoring |
| Workflow | Face detected → Select E/X → Log | Continuous logging |
| Duplicate Prevention | Prevents duplicates | May log multiple times |
| User Interaction | Required (Press E/X/F) | Automatic |
| Best For | School gates/checkpoints | Classroom/monitoring |

**Start Interactive Mode:**
```bash
python recognize_video_school.py ... --mode interactive
```

**Start Video Mode:**
```bash
python recognize_video_school.py ... --mode video
```

---

## 📱 Notification Samples

When a student is recognized:

### ✅ Normal Entry
```
SMS to Parent:
"✓ Sameer Patel has ENTERED school at 08:15. School ID: ATTEND-SYSTEM"
```

### ⏰ Late Arrival Alert
```
SMS to Parent:
"ALERT: Sameer Patel marked as LATE arrival at 08:45 
(School starts at 08:00). School ID: ATTEND-SYSTEM"
```

### ❌ Absence Alert (if marked manually)
```
SMS to Parent:
"ALERT: Sameer Patel is marked ABSENT on 20-03-2024. 
School ID: ATTEND-SYSTEM"
```

---

## 🐛 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Cannot connect to database" | Start XAMPP MySQL, check credentials |
| "No faces detected" | Improve lighting, position face closer |
| "Recognition rate low" | Retrain with more student images |
| "SMS not sending" | Verify Twilio account, add phone numbers to DB |
| "Port 5000 already in use" | Change port in `config.py` or kill process |
| "Model files not found" | Download from opencv repo or check `Models/` folder |

---

## 📚 File Reference

| File | Purpose |
|------|---------|
| `recognize_video_school.py` | **Main attendance system** |
| `app.py` | Web dashboard backend |
| `database.py` | Database operations |
| `config.py` | System configuration |
| `notifications.py` | SMS notifications |
| `setup.py` | Initial setup script |
| `attendance_db.sql` | Database schema |
| `templates/` | Web interface HTML |

---

## 🎯 Typical School Day Workflow

8:00 AM - School Starts
↓
Student Scans Face → System (marks ENTRY)
↓
SMS: "Sameer arrived at 08:05" → Parent
↓
... (Student in class/activities)
↓
3:30 PM - School Ends
↓
Student Scans Face → System (marks EXIT)
↓
SMS: "Sameer left at 15:35" → Parent
↓
End of Day
↓
Teacher/Admin Checks Daily Report on Dashboard
↓
See: 42 present, 3 absent, 2 late
↓
Archive & Send to Principal

---

## 📞 Support Commands

```bash
# Check if all dependencies are installed
pip list | grep -E "flask|mysql|pandas|opencv"

# Test database connection
python -c "from database import DatabaseConnection; db = DatabaseConnection(); db.connect()"

# Check Python version
python --version

# View logs
tail -100 logs/*.log  # On Mac/Linux
Get-Content logs/*.log -Tail 100  # On Windows
```

---

## ✨ Next Advanced Features (Coming Soon)

- 📧 Email reports to parents
- 📊 Advanced analytics dashboard
- 🔔 Notifications via WhatsApp
- 📷 PDF report generation
- 🎓 Integration with academic system
- 👨‍💼 Staff attendance tracking
- 🚌 Bus/Transport tracking

---

## 🔐 Security Checklist

- [ ] Change MySQL password
- [ ] Use HTTPS for production
- [ ] Add authentication to dashboard
- [ ] Encrypt Twilio credentials
- [ ] Regular database backups
- [ ] Restrict file permissions
- [ ] Monitor access logs

---

**🎉 You're all set! Start tracking attendance like a pro!**

Questions? Check `SCHOOL_SETUP_GUIDE.md` for detailed documentation.
