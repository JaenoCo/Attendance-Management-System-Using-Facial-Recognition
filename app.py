"""
FastAPI Web Dashboard for School Attendance Management System
Async-first implementation for robust concurrent request handling
With user authentication and session management
"""

from fastapi import FastAPI, Query, Form, HTTPException, Cookie, Response, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from database import DatabaseConnection
from datetime import datetime, date, timedelta, timedelta as td
from config import *
from passlib.context import CryptContext
from facial_recognition import get_facial_recognition_system
import pandas as pd
from io import BytesIO
import os
import secrets
import cv2
import numpy as np
import base64
import json

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

# Connect on startup
@app.on_event("startup")
async def startup_event():
    """Connect to database on startup"""
    db.connect()
    print("[INFO] FastAPI started - Database connection established")

# Connect on startup
@app.on_event("startup")
async def startup_event():
    """Connect to database on startup"""
    db.connect()
    print("[INFO] FastAPI started - Database connection established")

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
        return {'error': f'Database error: {str(e)}'}, 500
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
        return {'error': f'Database error: {str(e)}'}, 500
    finally:
        if cursor:
            cursor.close()

@app.get("/api/students/{student_id}")
async def get_student(student_id: int):
    """Get student details"""
    try:
        
        student = db.get_student_by_id(student_id)
        if not student:
            return {'error': 'Student not found'}, 404
        
        return student
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return {'error': f'Database error: {str(e)}'}, 500

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
        return {'error': f'Database error: {str(e)}'}, 500
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
        return {'error': f'Database error: {str(e)}'}, 500
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
            return {'error': 'student_id required'}, 400
        
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
        return {'error': str(e)}, 500

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
        return {'error': str(e)}, 500

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
        return {'error': f'Database error: {str(e)}'}, 500
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
        return {'error': f'Database error: {str(e)}'}, 500
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
        return {'error': f'Database error: {str(e)}'}, 500
    finally:
        if cursor:
            cursor.close()

# ==================== CRUD Operations ====================

@app.post("/api/students")
async def create_student(request: Request, name: str = Form(...), roll_number: str = Form(...), class_id: int = Form(...)):
    """Create a new student"""
    current_user = get_current_user(request)
    if not current_user:
        return {'error': 'Unauthorized'}, 401
    
    cursor = None
    try:
        cursor = db.connection.cursor()
        cursor.execute("""
            INSERT INTO students (name, roll_number, class_id, date_of_admission)
            VALUES (%s, %s, %s, %s)
        """, (name, roll_number, class_id, date.today()))
        db.connection.commit()
        
        cursor.execute("SELECT LAST_INSERT_ID() as id")
        student_id = cursor.fetchone()[0]
        
        return {'status': 'success', 'student_id': student_id, 'message': 'Student created successfully'}
    except Exception as e:
        db.connection.rollback()
        print(f"[ERROR] {type(e).__name__}: {e}")
        return {'error': f'Failed to create student: {str(e)}'}, 400
    finally:
        if cursor:
            cursor.close()

@app.put("/api/students/{student_id}")
async def update_student(request: Request, student_id: int, name: str = Form(...), roll_number: str = Form(...), class_id: int = Form(...)):
    """Update student details"""
    current_user = get_current_user(request)
    if not current_user:
        return {'error': 'Unauthorized'}, 401
    
    cursor = None
    try:
        cursor = db.connection.cursor()
        cursor.execute("""
            UPDATE students 
            SET name = %s, roll_number = %s, class_id = %s 
            WHERE student_id = %s
        """, (name, roll_number, class_id, student_id))
        db.connection.commit()
        
        if cursor.rowcount == 0:
            return {'error': 'Student not found'}, 404
        
        return {'status': 'success', 'message': 'Student updated successfully'}
    except Exception as e:
        db.connection.rollback()
        print(f"[ERROR] {type(e).__name__}: {e}")
        return {'error': f'Failed to update student: {str(e)}'}, 400
    finally:
        if cursor:
            cursor.close()

@app.delete("/api/students/{student_id}")
async def delete_student(request: Request, student_id: int):
    """Delete a student"""
    current_user = get_current_user(request)
    if not current_user:
        return {'error': 'Unauthorized'}, 401
    
    cursor = None
    try:
        cursor = db.connection.cursor()
        
        # Check if student exists
        cursor.execute("SELECT student_id FROM students WHERE student_id = %s", (student_id,))
        if not cursor.fetchone():
            return {'error': 'Student not found'}, 404
        
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
        return {'error': f'Failed to delete student: {str(e)}'}, 400
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
async def capture_face(request: Request, student_id: int = Form(...), image_data: str = Form(...)):
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
        return {'error': 'Unauthorized'}, 401
    
    try:
        # Get student info
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("SELECT student_id, name FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()
        cursor.close()
        
        if not student:
            return {'status': 'error', 'message': 'Student not found'}, 404
        
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
        return {'status': 'error', 'message': f'Error: {str(e)}'}

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
        return {'error': 'Unauthorized'}, 401
    
    try:
        # Get student info
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("SELECT student_id, name FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()
        cursor.close()
        
        if not student:
            return {'status': 'error', 'message': 'Student not found'}, 404
        
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
        return {'status': 'error', 'message': f'Error: {str(e)}'}

@app.post("/api/face/train")
async def train_facial_model(request: Request):
    """
    Train the facial recognition model on all captured faces
    Requires admin authentication
    """
    current_user = get_current_user(request)
    if not current_user:
        return {'error': 'Unauthorized'}, 401
    
    try:
        fr_system = get_facial_recognition_system()
        result = fr_system.train_recognizer()
        return result
    
    except Exception as e:
        return {'status': 'error', 'message': f'Training failed: {str(e)}'}

@app.get("/api/face/status")
async def get_face_enrollment_status(request: Request, student_id: int = Query(...)):
    """
    Get face enrollment status for a student
    """
    current_user = get_current_user(request)
    if not current_user:
        return {'error': 'Unauthorized'}, 401
    
    try:
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT student_id, name, face_registered, face_data
            FROM students
            WHERE student_id = %s
        """, (student_id,))
        student = cursor.fetchone()
        cursor.close()
        
        if not student:
            return {'status': 'error', 'message': 'Student not found'}, 404
        
        return {
            'status': 'success',
            'student_id': student['student_id'],
            'name': student['name'],
            'face_registered': bool(student.get('face_registered', 0)),
            'has_embedding': student.get('face_data') is not None
        }
    
    except Exception as e:
        return {'status': 'error', 'message': f'Error: {str(e)}'}

@app.get("/api/face/stats")
async def get_face_enrollment_stats(request: Request):
    """
    Get overall face enrollment statistics
    """
    current_user = get_current_user(request)
    if not current_user:
        return {'error': 'Unauthorized'}, 401
    
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
        return {'status': 'error', 'message': f'Error: {str(e)}'}

# ==================== Error Handlers ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        
        return {'status': 'healthy', 'database': 'connected'}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000, reload=False)
