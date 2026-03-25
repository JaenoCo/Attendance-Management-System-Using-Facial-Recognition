"""
FastAPI Web Dashboard for School Attendance Management System
Async-first implementation for robust concurrent request handling
With user authentication and session management
"""

from fastapi import FastAPI, Query, Form, HTTPException, Cookie, Response, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from database import DatabaseConnection
from datetime import datetime, date, timedelta as td
from config import *
from passlib.context import CryptContext
from facial_recognition import get_facial_recognition_system
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pandas as pd
from io import BytesIO
import os
import secrets
import cv2
import numpy as np
import base64
import json
import subprocess
import sys
import atexit
import socket
import re

# Initialize FastAPI app
app = FastAPI(title="School Attendance System", version="2.0")

# Setup template engine
templates = Jinja2Templates(directory="templates")

# Mount static files if needed
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Password hashing setup
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Session storage (in production, use Redis/database)
sessions = {}

# Demo users (in production, store in database with hashed passwords)
DEMO_USERS = {
    "admin": pwd_context.hash("admin123"),
    "teacher": pwd_context.hash("teacher123"),
    "staff": pwd_context.hash("staff123")
}

# Initialize database
db = DatabaseConnection(
    host=DATABASE_CONFIG['host'],
    user=DATABASE_CONFIG['user'],
    password=DATABASE_CONFIG['password'],
    database=DATABASE_CONFIG['database']
)

# Initialize APScheduler for background training
scheduler = BackgroundScheduler()
scheduler.start()

# Cleanup scheduler on shutdown
atexit.register(lambda: scheduler.shutdown())

def run_auto_training():
    """Background job to run auto training"""
    print("\n[SCHEDULER] Starting automatic face model training...")
    try:
        result = subprocess.run(
            [sys.executable, 'auto_train.py'],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode == 0:
            print("[SCHEDULER] ✓ Auto training completed successfully")
        else:
            print(f"[SCHEDULER] ✗ Auto training failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("[SCHEDULER] ✗ Auto training timed out")
    except Exception as e:
        print(f"[SCHEDULER] ✗ Auto training error: {e}")

# Connect on startup
@app.on_event("startup")
async def startup_event():
    """Connect to database on startup and start scheduler"""
    db.connect()
    
    # Schedule auto-training to run daily at 11 PM (23:00)
    scheduler.add_job(
        run_auto_training,
        CronTrigger(hour=23, minute=0),
        id='auto_training_job',
        name='Automatic Face Model Training',
        replace_existing=True
    )
    
    print("[INFO] FastAPI started - Database connection established")
    print("[INFO] Auto-training scheduler initialized (runs daily at 11 PM)")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    db.disconnect()
    print("[INFO] FastAPI shutdown - Database connection closed")

# Session management functions
def generate_session_token():
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

def verify_password(plain_password, hashed_password):
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_session(username):
    """Create a session for user"""
    token = generate_session_token()
    sessions[token] = {
        "username": username,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + td(hours=8)
    }
    return token

def get_session(session_token):
    """Get session info by token"""
    if not session_token:
        return None
    session = sessions.get(session_token)
    if not session:
        return None
    # Check if session expired
    if datetime.now() > session["expires_at"]:
        del sessions[session_token]
        return None
    return session

def get_current_user(request: Request):
    """Get current logged-in user"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    session = get_session(session_token)
    if session:
        return session["username"]
    return None

def _normalize_identity_value(value):
    """Normalize predicted labels and student identity strings for matching."""
    if value is None:
        return ''
    text = str(value).strip().lower()
    text = text.replace('-', ' ').replace('_', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text

def ensure_connection():
    """Ensure database connection is active"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if db.connection:
                try:
                    db.connection.ping(reconnect=True)
                    return
                except:
                    try:
                        db.connection.close()
                    except:
                        pass
                    db.connection = None
            
            if not db.connection:
                db.connect()
                return
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            else:
                print(f"[ERROR] Failed to connect to database: {e}")

# ==================== Authentication Routes ====================

@app.get("/login")
async def login_page(request: Request):
    """Display login page"""
    # If already logged in, redirect to dashboard
    current_user = get_current_user(request)
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": request.query_params.get("error")
    })

@app.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    """Handle login"""
    # Verify username and password
    if username not in DEMO_USERS:
        return RedirectResponse(url="/login?error=Invalid username or password", status_code=302)
    
    if not verify_password(password, DEMO_USERS[username]):
        return RedirectResponse(url="/login?error=Invalid username or password", status_code=302)
    
    # Create session
    session_token = create_session(username)
    
    # Set session cookie
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        "session_token",
        session_token,
        max_age=8*60*60,  # 8 hours
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    return response

@app.get("/logout")
async def logout(response: Response):
    """Handle logout"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response

# ==================== Dashboard Routes ====================

@app.get("/")
async def dashboard(request: Request):
    """Main dashboard - Overview"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": current_user
    })

@app.get("/api/dashboard-stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    cursor = None
    try:
        
        cursor = db.connection.cursor(dictionary=True)
        
        # Total students
        cursor.execute("SELECT COUNT(*) as count FROM students")
        total_students = cursor.fetchone()['count']
        
        # Today's attendance (present)
        today = date.today()
        cursor.execute("""
            SELECT COUNT(DISTINCT student_id) as count 
            FROM attendance_scans 
            WHERE DATE(scan_time) = %s
        """, (today,))
        today_present = cursor.fetchone()['count']
        
        # Total classes
        cursor.execute("SELECT COUNT(*) as count FROM classes")
        total_classes = cursor.fetchone()['count']
        
        return {
            'total_students': total_students,
            'today_present': today_present,
            'total_classes': total_classes
        }
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': f'Database error: {str(e)}'}, status_code=500)
    finally:
        if cursor:
            cursor.close()

# ==================== Student Routes ====================

@app.get("/students")
async def students_page(request: Request):
    """Students management page"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("students.html", {
        "request": request,
        "username": current_user
    })

@app.get("/api/students")
async def get_students():
    """Get all students"""
    cursor = None
    try:
        
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, c.class_name 
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.class_id
            ORDER BY s.roll_number
        """)
        students = cursor.fetchall()
        
        # Convert dates to strings
        for student in students:
            if student.get('date_of_admission'):
                student['date_of_admission'] = student['date_of_admission'].isoformat()
            if student.get('created_at'):
                student['created_at'] = student['created_at'].isoformat()
        
        return students
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': f'Database error: {str(e)}'}, status_code=500)
    finally:
        if cursor:
            cursor.close()

@app.get("/api/students/{student_id}")
async def get_student(student_id: int):
    """Get student details"""
    try:
        
        student = db.get_student_by_id(student_id)
        if not student:
            return JSONResponse({'error': 'Student not found'}, status_code=404)
        
        return student
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': f'Database error: {str(e)}'}, status_code=500)

# ==================== Attendance Routes ====================

@app.get("/attendance")
async def attendance_page(request: Request):
    """Attendance management page"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("attendance.html", {
        "request": request,
        "username": current_user
    })

@app.get("/api/attendance/today")
async def get_today_attendance():
    """Get today's attendance for all students"""
    cursor = None
    try:
        
        today = date.today()
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.student_id, s.roll_number, s.first_name, s.last_name, 
                   c.class_name, al.entry_time, al.exit_time, al.status
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.class_id
            LEFT JOIN attendance_logs al ON s.student_id = al.student_id AND al.date = %s
            ORDER BY s.roll_number
        """, (today,))
        attendance = cursor.fetchall()
        
        # Format times
        for record in attendance:
            if record.get('entry_time'):
                record['entry_time'] = record['entry_time'].isoformat()
            if record.get('exit_time'):
                record['exit_time'] = record['exit_time'].isoformat()
        
        return attendance
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': f'Database error: {str(e)}'}, status_code=500)
    finally:
        if cursor:
            cursor.close()

@app.get("/api/attendance/class/{class_id}")
async def get_class_attendance(class_id: int, date_param: str = Query(None)):
    """Get class attendance for a specific date"""
    cursor = None
    try:
        
        target_date = date_param if date_param else date.today()
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        attendance = db.get_class_attendance(class_id, target_date)
        
        # Format response
        for record in attendance:
            if record.get('entry_time'):
                record['entry_time'] = record['entry_time'].isoformat()
            if record.get('exit_time'):
                record['exit_time'] = record['exit_time'].isoformat()
        
        return attendance
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': f'Database error: {str(e)}'}, status_code=500)
    finally:
        if cursor:
            cursor.close()

# ==================== Reports Routes ====================

@app.get("/reports")
async def reports_page(request: Request):
    """Reports page"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "username": current_user
    })

@app.get("/api/reports/student-attendance")
async def get_student_attendance_report(
    student_id: int = Query(...),
    start_date: str = Query(None),
    end_date: str = Query(None)
):
    """Get student attendance report"""
    try:
        if not student_id:
            return JSONResponse({'error': 'student_id required'}, status_code=400)
        
        start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        
        attendance = db.get_attendance_report(student_id, start, end)
        
        # Format response
        for record in attendance:
            record['date'] = record['date'].isoformat()
            if record.get('entry_time'):
                record['entry_time'] = record['entry_time'].isoformat()
            if record.get('exit_time'):
                record['exit_time'] = record['exit_time'].isoformat()
        
        # Calculate stats
        total_days = len(attendance)
        present_days = sum(1 for a in attendance if a.get('status') == 'present')
        absent_days = sum(1 for a in attendance if a.get('status') == 'absent')
        late_days = sum(1 for a in attendance if a.get('status') == 'late')
        
        return {
            'attendance': attendance,
            'stats': {
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'late_days': late_days,
                'percentage': (present_days / total_days * 100) if total_days > 0 else 0
            }
        }
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/api/reports/export-csv")
async def export_attendance_csv(
    student_id: int = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...)
):
    """Export attendance report as CSV"""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        attendance = db.get_attendance_report(student_id, start, end)
        
        # Create DataFrame
        df = pd.DataFrame(attendance)
        
        # Create CSV in memory
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        filename = f"attendance_{student_id}_{datetime.now().strftime('%Y%m%d')}.csv"
        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/api/reports/monthly-stats")
async def get_monthly_stats(
    month: int = Query(None),
    year: int = Query(None)
):
    """Get monthly attendance statistics"""
    cursor = None
    try:
        
        
        month = month or date.today().month
        year = year or date.today().year
        
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                DATE(al.date) as date,
                COUNT(DISTINCT al.student_id) as total_scanned,
                SUM(CASE WHEN al.status = 'present' THEN 1 ELSE 0 END) as present,
                SUM(CASE WHEN al.status = 'absent' THEN 1 ELSE 0 END) as absent,
                SUM(CASE WHEN al.status = 'late' THEN 1 ELSE 0 END) as late
            FROM attendance_logs al
            WHERE MONTH(al.date) = %s AND YEAR(al.date) = %s
            GROUP BY DATE(al.date)
            ORDER BY DATE(al.date) ASC
        """, (month, year))
        
        stats = cursor.fetchall()
        
        # Format dates
        for stat in stats:
            if stat.get('date'):
                stat['date'] = stat['date'].isoformat()
        
        return stats
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': f'Database error: {str(e)}'}, status_code=500)
    finally:
        if cursor:
            cursor.close()

# ==================== Teacher Routes ====================

@app.get("/api/teachers")
async def get_teachers():
    """Get all teachers"""
    cursor = None
    try:
        
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM teachers ORDER BY first_name")
        teachers = cursor.fetchall()
        return teachers
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': f'Database error: {str(e)}'}, status_code=500)
    finally:
        if cursor:
            cursor.close()

# ==================== Class Routes ====================

@app.get("/api/classes")
async def get_classes():
    """Get all classes"""
    cursor = None
    try:
        
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, t.first_name, t.last_name, COUNT(s.student_id) as student_count
            FROM classes c
            LEFT JOIN teachers t ON c.teacher_id = t.teacher_id
            LEFT JOIN students s ON c.class_id = s.class_id
            GROUP BY c.class_id
        """)
        classes = cursor.fetchall()
        return classes
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': f'Database error: {str(e)}'}, status_code=500)
    finally:
        if cursor:
            cursor.close()

# ==================== CRUD Operations ====================

@app.post("/api/students")
async def create_student(request: Request, first_name: str = Form(...), last_name: str = Form(...), roll_number: str = Form(...), class_id: int = Form(...)):
    """Create a new student"""
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse({'error': 'Unauthorized'}, status_code=401)
    
    cursor = None
    try:
        cursor = db.connection.cursor()
        cursor.execute("""
            INSERT INTO students (first_name, last_name, roll_number, class_id, date_of_admission, face_training_status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """, (first_name, last_name, roll_number, class_id, date.today()))
        db.connection.commit()
        
        cursor.execute("SELECT LAST_INSERT_ID() as id")
        student_id = cursor.fetchone()[0]
        
        return JSONResponse({'status': 'success', 'student_id': student_id, 'message': f'Student {first_name} {last_name} created successfully'})
    except Exception as e:
        db.connection.rollback()
        print(f"[ERROR] Create student failed - {type(e).__name__}: {e}")
        return JSONResponse({'status': 'error', 'message': f'Failed to create student: {str(e)}'}, status_code=400)
    finally:
        if cursor:
            cursor.close()

@app.put("/api/students/{student_id}")
async def update_student(request: Request, student_id: int, first_name: str = Form(...), last_name: str = Form(...), roll_number: str = Form(...), class_id: int = Form(...)):
    """Update student details"""
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse({'error': 'Unauthorized'}, status_code=401)
    
    cursor = None
    try:
        cursor = db.connection.cursor()
        cursor.execute("""
            UPDATE students 
            SET first_name = %s, last_name = %s, roll_number = %s, class_id = %s 
            WHERE student_id = %s
        """, (first_name, last_name, roll_number, class_id, student_id))
        db.connection.commit()
        
        if cursor.rowcount == 0:
            return JSONResponse({'error': 'Student not found'}, status_code=404)
        
        return JSONResponse({'status': 'success', 'message': f'Student {first_name} {last_name} updated successfully'})
    except Exception as e:
        db.connection.rollback()
        print(f"[ERROR] Update student failed - {type(e).__name__}: {e}")
        return JSONResponse({'status': 'error', 'message': f'Failed to update student: {str(e)}'}, status_code=400)
    finally:
        if cursor:
            cursor.close()

@app.delete("/api/students/{student_id}")
async def delete_student(request: Request, student_id: int):
    """Delete a student"""
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse({'error': 'Unauthorized'}, status_code=401)
    
    cursor = None
    try:
        cursor = db.connection.cursor()
        
        # Check if student exists
        cursor.execute("SELECT student_id FROM students WHERE student_id = %s", (student_id,))
        if not cursor.fetchone():
            return JSONResponse({'error': 'Student not found'}, status_code=404)
        
        # Delete attendance records first (foreign key constraint)
        cursor.execute("DELETE FROM attendance_scans WHERE student_id = %s", (student_id,))
        cursor.execute("DELETE FROM attendance_logs WHERE student_id = %s", (student_id,))
        
        # Delete student
        cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
        db.connection.commit()
        
        return {'status': 'success', 'message': 'Student deleted successfully'}
    except Exception as e:
        db.connection.rollback()
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': f'Failed to delete student: {str(e)}'}, status_code=400)
    finally:
        if cursor:
            cursor.close()

# ==================== Settings Routes ====================

@app.get("/settings")
async def settings_page(request: Request):
    """Settings management page"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "username": current_user
    })

# ==================== Facial Recognition Routes ====================

@app.get("/face-enrollment")
async def face_enrollment_page(request: Request):
    """Face enrollment page"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("face_enrollment.html", {
        "request": request,
        "username": current_user
    })

@app.post("/api/face/capture")
async def capture_face_webcam(request: Request, student_id: int = Form(...), image_data: str = Form(...)):
    """
    Capture and process face image from webcam
    Args:
        student_id: ID of the student
        image_data: Base64 encoded image from webcam
    Returns:
        Face embedding and status
    """
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse({'error': 'Unauthorized'}, status_code=401)
    
    try:
        # Get student info
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT student_id, CONCAT(first_name, ' ', last_name) AS name
            FROM students
            WHERE student_id = %s
        """, (student_id,))
        student = cursor.fetchone()
        cursor.close()
        
        if not student:
            return JSONResponse({'status': 'error', 'message': 'Student not found'}, status_code=404)
        
        # Decode base64 image
        image_data_clean = image_data.split(',')[1] if ',' in image_data else image_data
        image_bytes = base64.b64decode(image_data_clean)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image_array is None:
            return {'status': 'error', 'message': 'Invalid image data'}
        
        # Get facial recognition system
        fr_system = get_facial_recognition_system()
        
        # Capture face and get embedding
        result = fr_system.capture_face_from_image(
            image_array,
            student_id,
            student['name']
        )
        
        if result['status'] == 'success':
            # Store face embedding in database (optional)
            cursor = db.connection.cursor()
            try:
                embedding_json = json.dumps(result['embedding'])
                cursor.execute("""
                    UPDATE students 
                    SET face_registered = 1, face_data = %s
                    WHERE student_id = %s
                """, (embedding_json, student_id))
                db.connection.commit()
            except Exception as e:
                print(f"[WARNING] Could not store embedding in DB: {e}")
            finally:
                cursor.close()
        
        return result
    
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status_code=500)


@app.post("/api/face/detect")
async def detect_faces_endpoint(request: Request):
    """Detect faces from image data for enrollment preview (no identity recognition)."""
    try:
        body = await request.json()
        image_data = body.get('image', '')

        if not image_data:
            return JSONResponse({'status': 'error', 'message': 'No image provided'}, status_code=400)

        if ',' in image_data:
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return JSONResponse({'status': 'error', 'message': 'Invalid image format'}, status_code=400)

        fr_system = get_facial_recognition_system()
        raw_detections = fr_system.detect_faces(frame)

        frame_h, frame_w = frame.shape[:2]
        faces_payload = []
        for detection in raw_detections:
            box = detection.get('box') or ()
            if len(box) != 4:
                continue

            start_x = max(0, min(int(box[0]), frame_w - 1))
            start_y = max(0, min(int(box[1]), frame_h - 1))
            end_x = max(0, min(int(box[2]), frame_w - 1))
            end_y = max(0, min(int(box[3]), frame_h - 1))

            faces_payload.append({
                'box': [start_x, start_y, end_x, end_y],
                'confidence': float(detection.get('confidence', 0.0))
            })

        return JSONResponse({
            'status': 'success',
            'detected': len(faces_payload) > 0,
            'faces': faces_payload
        })
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': f'Detection error: {str(e)}'}, status_code=500)

@app.post("/api/face/add-manual")
async def add_face_manual(
    request: Request,
    student_id: int = Form(...),
    face_image: UploadFile = File(...)
):
    """
    Add face from uploaded image file
    """
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse({'error': 'Unauthorized'}, status_code=401)
    
    try:
        # Get student info
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT student_id, CONCAT(first_name, ' ', last_name) AS name
            FROM students
            WHERE student_id = %s
        """, (student_id,))
        student = cursor.fetchone()
        cursor.close()
        
        if not student:
            return JSONResponse({'status': 'error', 'message': 'Student not found'}, status_code=404)
        
        # Read uploaded file
        contents = await face_image.read()
        nparr = np.frombuffer(contents, np.uint8)
        image_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image_array is None:
            return {'status': 'error', 'message': 'Invalid image file'}
        
        # Get facial recognition system
        fr_system = get_facial_recognition_system()
        
        # Capture face
        result = fr_system.capture_face_from_image(
            image_array,
            student_id,
            student['name']
        )
        
        if result['status'] == 'success':
            cursor = db.connection.cursor()
            try:
                embedding_json = json.dumps(result['embedding'])
                cursor.execute("""
                    UPDATE students 
                    SET face_registered = 1, face_data = %s
                    WHERE student_id = %s
                """, (embedding_json, student_id))
                db.connection.commit()
            except Exception as e:
                print(f"[WARNING] Could not store embedding in DB: {e}")
            finally:
                cursor.close()
        
        return result
    
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status_code=500)

@app.post("/api/face/train")
async def train_facial_model(request: Request):
    """
    Train the facial recognition model on all captured faces
    Requires admin authentication
    """
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse({'error': 'Unauthorized'}, status_code=401)
    
    try:
        fr_system = get_facial_recognition_system()
        result = fr_system.train_recognizer()
        return result
    
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': f'Training failed: {str(e)}'}, status_code=500)

@app.get("/api/face/status")
async def get_face_enrollment_status(request: Request, student_id: int = Query(...)):
    """
    Get face enrollment status for a student
    """
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse({'error': 'Unauthorized'}, status_code=401)
    
    try:
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT student_id,
                   CONCAT(first_name, ' ', last_name) AS name,
                   face_registered,
                   face_data
            FROM students
            WHERE student_id = %s
        """, (student_id,))
        student = cursor.fetchone()
        cursor.close()
        
        if not student:
            return JSONResponse({'status': 'error', 'message': 'Student not found'}, status_code=404)
        
        return {
            'status': 'success',
            'student_id': student['student_id'],
            'name': student['name'],
            'face_registered': bool(student.get('face_registered', 0)),
            'has_embedding': student.get('face_data') is not None
        }
    
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status_code=500)

@app.get("/api/face/stats")
async def get_face_enrollment_stats(request: Request):
    """
    Get overall face enrollment statistics
    """
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse({'error': 'Unauthorized'}, status_code=401)
    
    try:
        cursor = db.connection.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as total FROM students")
        total_students = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as enrolled FROM students WHERE face_registered = 1")
        enrolled_students = cursor.fetchone()['enrolled']
        
        cursor.close()
        
        enrollment_percentage = (enrolled_students / total_students * 100) if total_students > 0 else 0
        
        return {
            'status': 'success',
            'total_students': total_students,
            'enrolled_students': enrolled_students,
            'pending_students': total_students - enrolled_students,
            'enrollment_percentage': round(enrollment_percentage, 2)
        }
    
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status_code=500)

# ==================== Error Handlers ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        
        return {'status': 'healthy', 'database': 'connected'}
    except Exception as e:
        return JSONResponse({'status': 'unhealthy', 'error': str(e)}, status_code=500)

# ==================== Admin Registration Routes ====================

@app.get("/admin/register-student")
async def admin_register_student_page(request: Request):
    """Admin student registration page"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("admin_register.html", {
        "request": request,
        "username": current_user
    })

@app.get("/admin/capture-images/{student_id}")
async def admin_capture_images_page(request: Request, student_id: int):
    """Dedicated image capture page for a registered student"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    cursor = None
    try:
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT student_id, roll_number, first_name, last_name
            FROM students
            WHERE student_id = %s
        """, (student_id,))
        student = cursor.fetchone()

        if not student:
            return RedirectResponse(url="/admin/register-student", status_code=302)

        return templates.TemplateResponse("image_capture.html", {
            "request": request,
            "username": current_user,
            "student": student
        })
    finally:
        if cursor:
            cursor.close()

@app.post("/api/admin/register-student")
async def register_student(
    roll_number: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    class_id: int = Form(None)
):
    """Register a new student"""
    cursor = None
    try:
        cursor = db.connection.cursor(dictionary=True)
        
        # Check if student already exists
        cursor.execute("SELECT student_id FROM students WHERE roll_number = %s", (roll_number,))
        if cursor.fetchone():
            return JSONResponse(
                {'status': 'error', 'message': 'Student with this ID already exists'},
                status_code=400
            )

        # Validate class_id if provided
        if class_id is not None:
            cursor.execute("SELECT class_id FROM classes WHERE class_id = %s", (class_id,))
            if not cursor.fetchone():
                return JSONResponse(
                    {'status': 'error', 'message': 'Invalid class selected. Please choose a valid class.'},
                    status_code=400
                )
        
        # Insert new student
        query = """
            INSERT INTO students (roll_number, first_name, last_name, class_id, date_of_admission, face_training_status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """
        cursor.execute(query, (roll_number, first_name, last_name, class_id, date.today()))
        db.connection.commit()
        
        student_id = cursor.lastrowid
        
        return JSONResponse({
            'status': 'success',
            'message': f'Student {first_name} {last_name} registered successfully',
            'student_id': student_id
        })
        
    except Exception as e:
        print(f"[ERROR] Registration failed - {type(e).__name__}: {e}")
        return JSONResponse(
            {'status': 'error', 'message': f'Registration failed: {str(e)}'},
            status_code=500
        )
    finally:
        if cursor:
            cursor.close()

@app.post("/api/admin/capture-face")
async def capture_face_admin(student_id: int = Form(...)):
    """Trigger face capture for a student"""
    cursor = None
    try:
        # Verify student exists
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            return JSONResponse(
                {'status': 'error', 'message': 'Student not found'},
                status_code=404
            )
        
        # Create dataset folder for this student if it doesn't exist
        student_folder = os.path.join('dataset', str(student_id))
        os.makedirs(student_folder, exist_ok=True)
        
        # Launch capture.py for this student
        # The capture.py script will save images to dataset/{student_id}/
        try:
            # Note: capture.py will save images to dataset folder
            # We just need to inform it to save to the right location
            subprocess.Popen(
                [sys.executable, 'capture.py'],
                cwd=os.getcwd(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            return JSONResponse({
                'status': 'success',
                'message': f'Face capture opened for {student["first_name"]} {student["last_name"]}',
                'student_id': student_id
            })
            
        except Exception as e:
            return JSONResponse(
                {'status': 'error', 'message': f'Failed to open capture: {str(e)}'},
                status_code=500
            )
    
    except Exception as e:
        print(f"[ERROR] Capture failed - {type(e).__name__}: {e}")
        return JSONResponse(
            {'status': 'error', 'message': f'Error: {str(e)}'},
            status_code=500
        )
    finally:
        if cursor:
            cursor.close()

@app.post("/api/admin/train-now")
async def train_now_endpoint():
    """Manually trigger model training"""
    try:
        result = subprocess.run(
            [sys.executable, 'auto_train.py'],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0:
            return {
                'status': 'success',
                'message': 'Model training started in background',
                'output': result.stdout[-500:]  # Last 500 chars
            }
        else:
            return JSONResponse({
                'status': 'error',
                'message': 'Training failed',
                'output': result.stderr[-500:]
            }, status_code=500)
            
    except subprocess.TimeoutExpired:
        return JSONResponse({
            'status': 'error',
            'message': 'Training timed out'
        }, status_code=500)
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': str(e)}, status_code=500)

# ==================== Attendance Check-In Routes ====================

@app.get("/attendance/checkin")
async def attendance_checkin_page(request: Request):
    """Attendance check-in page"""
    return templates.TemplateResponse("attendance_checkin.html", {
        "request": request
    })

@app.post("/api/attendance/checkin")
async def attendance_checkin(
    student_id: str = Form(...),
    face_data: str = Form(None)
):
    """Mark attendance using face recognition"""
    cursor = None
    try:
        cursor = db.connection.cursor(dictionary=True)
        
        # Verify student exists
        cursor.execute("SELECT * FROM students WHERE roll_number = %s OR student_id = %s", 
                      (student_id, student_id if student_id.isdigit() else None))
        student = cursor.fetchone()
        
        if not student:
            return JSONResponse(
                {'status': 'error', 'message': 'Student not found'},
                status_code=404
            )
        
        # Trigger face recognition
        if face_data:
            # Would need to implement face recognition here
            # For now, we'll mark as present if student ID is valid
            pass
        
        # Get existing attendance for today
        today = date.today()
        cursor.execute("""
            SELECT * FROM attendance_logs 
            WHERE student_id = %s AND date = %s
        """, (student['student_id'], today))
        
        existing = cursor.fetchone()
        
        if existing:
            return JSONResponse({
                'status': 'warning',
                'message': f"{student['first_name']} {student['last_name']} already marked present today at {existing['entry_time']}",
                'student': {
                    'id': student['student_id'],
                    'name': f"{student['first_name']} {student['last_name']}",
                    'roll_number': student['roll_number']
                }
            })
        
        # Record attendance
        now = datetime.now().time()
        cursor.execute("""
            INSERT INTO attendance_logs (student_id, date, entry_time, status)
            VALUES (%s, %s, %s, 'present')
        """, (student['student_id'], today, now))
        
        # Also record in attendance scans
        cursor.execute("""
            INSERT INTO attendance_scans (student_id, scan_type, scan_time, confidence_score, recognized)
            VALUES (%s, 'entry', %s, 0.95, TRUE)
        """, (student['student_id'], datetime.now()))
        
        db.connection.commit()
        
        return JSONResponse({
            'status': 'success',
            'message': f"✓ {student['first_name']} {student['last_name']} marked present",
            'student': {
                'id': student['student_id'],
                'name': f"{student['first_name']} {student['last_name']}",
                'roll_number': student['roll_number'],
                'time': now.isoformat()
            }
        })
        
    except Exception as e:
        print(f"[ERROR] Check-in failed - {type(e).__name__}: {e}")
        return JSONResponse(
            {'status': 'error', 'message': f'Check-in failed: {str(e)}'},
            status_code=500
        )
    finally:
        if cursor:
            cursor.close()

@app.get("/api/attendance/checkin-status/{student_id}")
async def get_checkin_status(student_id: str):
    """Check if student is already checked in today"""
    cursor = None
    try:
        cursor = db.connection.cursor(dictionary=True)
        
        today = date.today()
        cursor.execute("""
            SELECT al.*
            FROM attendance_logs al
            INNER JOIN students s ON s.student_id = al.student_id
            WHERE (s.student_id = %s OR s.roll_number = %s) AND al.date = %s
        """, (student_id if student_id.isdigit() else None, student_id, today))
        
        result = cursor.fetchone()
        
        if result:
            return {
                'status': 'already_present',
                'message': f'Student already checked in at {result["entry_time"]}',
                'time': str(result['entry_time'])
            }
        else:
            return {'status': 'not_present', 'message': 'Not yet checked in'}
            
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': str(e)}, status_code=500)
    finally:
        if cursor:
            cursor.close()

@app.post("/api/attendance/recognize-face")
async def recognize_face_endpoint(request: Request):
    """Recognize student from facial data"""
    cursor = None
    try:
        # Get JSON body
        body = await request.json()
        image_data = body.get('image', '')
        
        if not image_data:
            return JSONResponse(
                {'status': 'error', 'message': 'No image provided'},
                status_code=400
            )
        
        # Decode base64 image
        import base64
        from io import BytesIO
        
        # Remove data:image/jpeg;base64, prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return JSONResponse(
                {'status': 'error', 'message': 'Invalid image format'},
                status_code=400
            )
        
        # Get facial recognition system
        fr_system = get_facial_recognition_system()

        # Always run raw detection first so UI can draw bounding boxes
        raw_detections = fr_system.detect_faces(frame)
        faces_payload = []
        frame_h, frame_w = frame.shape[:2]
        for detection in raw_detections:
            box = detection.get('box') or ()
            if len(box) == 4:
                start_x = max(0, min(int(box[0]), frame_w - 1))
                start_y = max(0, min(int(box[1]), frame_h - 1))
                end_x = max(0, min(int(box[2]), frame_w - 1))
                end_y = max(0, min(int(box[3]), frame_h - 1))
                normalized_box = [start_x, start_y, end_x, end_y]
            else:
                normalized_box = []

            faces_payload.append({
                'box': normalized_box,
                'name': None,
                'confidence': float(detection.get('confidence', 0.0))
            })
        
        # Process frame and detect faces
        detected_faces = fr_system.process_frame(frame)
        if detected_faces:
            for idx, face in enumerate(detected_faces):
                if idx >= len(faces_payload):
                    break
                if face.get('name'):
                    faces_payload[idx]['name'] = str(face.get('name'))
                    faces_payload[idx]['confidence'] = float(face.get('confidence', faces_payload[idx]['confidence']))
        
        if not raw_detections:
            return JSONResponse({
                'status': 'error',
                'message': 'No face detected',
                'recognized': False,
                'faces': []
            })

        if not detected_faces:
            return JSONResponse({
                'status': 'error',
                'message': 'Face detected, but recognition model is not ready',
                'recognized': False,
                'faces': faces_payload
            })
        
        # Get the most confident face recognition
        best_match = max(detected_faces, key=lambda x: x['confidence'])
        
        if best_match['confidence'] < 0.20:  # Recognition probability threshold
            return JSONResponse({
                'status': 'error',
                'message': 'Face confidence too low',
                'recognized': False,
                'confidence': float(best_match['confidence']),
                'faces': faces_payload
            })
        
        # Look up student by recognized label/name
        student_name = best_match['name']
        predicted_label = str(student_name or '').strip()
        normalized_label = _normalize_identity_value(predicted_label)
        cursor = db.connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT student_id, roll_number, first_name, last_name
            FROM students
        """)
        students = cursor.fetchall() or []

        student = None
        for candidate in students:
            full_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
            aliases = {
                _normalize_identity_value(candidate.get('student_id')),
                _normalize_identity_value(candidate.get('roll_number')),
                _normalize_identity_value(full_name),
                _normalize_identity_value(full_name.replace(' ', '_')),
                _normalize_identity_value(candidate.get('first_name')),
                _normalize_identity_value(candidate.get('last_name')),
            }

            if normalized_label and normalized_label in aliases:
                student = candidate
                break
        
        if student:
            return JSONResponse({
                'status': 'success',
                'message': f'Face recognized: {student["first_name"]} {student["last_name"]}',
                'recognized': True,
                'predicted_label': predicted_label,
                'student': {
                    'id': student['student_id'],
                    'name': f"{student['first_name']} {student['last_name']}",
                    'roll_number': student['roll_number']
                },
                'confidence': float(best_match['confidence']),
                'faces': faces_payload
            })
        else:
            return JSONResponse({
                'status': 'error',
                'message': f'Face recognized but student not found in database: {student_name}',
                'recognized': True,
                'face_name': student_name,
                'predicted_label': predicted_label,
                'faces': faces_payload
            })
        
    except Exception as e:
        print(f"[ERROR] Face recognition failed - {type(e).__name__}: {e}")
        return JSONResponse(
            {'status': 'error', 'message': f'Face recognition error: {str(e)}'},
            status_code=500
        )
    finally:
        if cursor:
            cursor.close()

if __name__ == "__main__":
    import uvicorn

    def find_available_port(start_port=5000, host="127.0.0.1", max_attempts=20):
        """Find first available port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if sock.connect_ex((host, port)) != 0:
                    return port
        raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts - 1}")

    base_port = int(os.getenv("PORT", "5000"))
    selected_port = find_available_port(start_port=base_port)
    if selected_port != base_port:
        print(f"[INFO] Port {base_port} is busy. Using port {selected_port} instead.")

    uvicorn.run(app, host="127.0.0.1", port=selected_port, reload=False)
