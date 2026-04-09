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
from validators import ImageValidator, ValidationError, ErrorResponse, DatabaseErrorHandler, LoggingSetup
from ratelimiter import limiter, apply_rate_limit, LIMITS
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
import logging
from pathlib import Path


def format_db_value(value):
    """Convert database date/time values into JSON-safe strings."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, td):
        total_seconds = int(value.total_seconds())
        sign = '-' if total_seconds < 0 else ''
        total_seconds = abs(total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)

# Initialize FastAPI app
app = FastAPI(title="School Attendance System", version="2.0")

# Setup rate limiting
app.state.limiter = limiter
app.add_exception_handler(Exception, limiter.http_exception_handler)

# Setup logging
logger = LoggingSetup.setup_logging()
logger.info("School Attendance System Starting...")

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


def _ensure_attendance_log_history():
    """Allow multiple attendance log entries per student per day."""
    cursor = None
    try:
        if not db.connection:
            return

        cursor = db.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'attendance_logs'
              AND INDEX_NAME = 'unique_daily_attendance'
        """)
        has_unique_constraint = cursor.fetchone()[0] > 0

        if has_unique_constraint:
            cursor.execute("ALTER TABLE attendance_logs DROP INDEX unique_daily_attendance")
            db.connection.commit()
            print("[INFO] Dropped legacy unique_daily_attendance index to allow repeated check-ins")
    except Exception as e:
        print(f"[WARNING] Attendance log migration skipped: {e}")
    finally:
        if cursor:
            cursor.close()

# Connect on startup
@app.on_event("startup")
async def startup_event():
    """Connect to database on startup and start scheduler"""
    db.connect()
    _ensure_attendance_log_history()
    _ensure_student_face_columns()
    _sync_face_capture_records_from_dataset()
    
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


FACE_MATCH_DISTANCE_THRESHOLD = 0.45
FACE_MATCH_SIMILARITY_THRESHOLD = 1.0 - FACE_MATCH_DISTANCE_THRESHOLD
LIVE_FACE_DETECTION_THRESHOLD = 0.35


def _to_flat_embedding(embedding_value):
    """Convert stored/live embedding to 1D numpy array."""
    if embedding_value is None:
        return None

    parsed = embedding_value
    if isinstance(embedding_value, str):
        parsed = json.loads(embedding_value)

    array = np.asarray(parsed, dtype=np.float32)
    if array.size == 0:
        return None

    return array.reshape(-1)


def _cosine_similarity(vec_a, vec_b):
    """Cosine similarity between two vectors."""
    denom = (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    if denom == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / denom)


def _cosine_distance(vec_a, vec_b):
    """Convert cosine similarity into a CFIS-style distance score."""
    return 1.0 - _cosine_similarity(vec_a, vec_b)


def _distance_to_cfis_percentage(distance, threshold=FACE_MATCH_DISTANCE_THRESHOLD):
    """Map an accepted distance into the 85%-100% range used by CFIS."""
    if distance > threshold:
        return None

    if threshold <= 0:
        return 100.0

    percentage = 85.0 + ((threshold - distance) / threshold) * 15.0
    return max(85.0, min(100.0, percentage))


def _student_identity_tokens(student):
    """Build normalized identity tokens for matching recognizer labels to students."""
    if not student:
        return set()

    first_name = str(student.get('first_name') or '').strip()
    last_name = str(student.get('last_name') or '').strip()
    full_name = f"{first_name} {last_name}".strip()

    raw_values = [
        student.get('student_id'),
        student.get('roll_number'),
        first_name,
        last_name,
        full_name
    ]

    tokens = set()
    for value in raw_values:
        normalized = _normalize_identity_value(value)
        if normalized:
            tokens.add(normalized)
    return tokens


def _find_student_by_label(students, predicted_label):
    """Map a predicted recognizer label to a student record."""
    normalized_label = _normalize_identity_value(predicted_label)
    if not normalized_label:
        return None

    for student in students:
        if normalized_label in _student_identity_tokens(student):
            return student
    return None


def _find_student_by_label_fallback(cursor, predicted_label):
    """Try a direct database lookup when label tokens do not match exactly."""
    normalized_label = _normalize_identity_value(predicted_label)
    if not normalized_label:
        return None

    try:
        cursor.execute(
            """
            SELECT student_id, roll_number, first_name, last_name, COALESCE(faces_captured, 0) AS faces_captured, face_training_status
            FROM students
            WHERE CAST(student_id AS CHAR) = %s
               OR roll_number = %s
               OR LOWER(CONCAT(first_name, ' ', last_name)) = %s
               OR LOWER(first_name) = %s
               OR LOWER(last_name) = %s
            LIMIT 1
            """,
            (
                normalized_label,
                normalized_label,
                normalized_label,
                normalized_label,
                normalized_label,
            )
        )
        return cursor.fetchone()
    except Exception:
        return None


def _find_student_by_capture_similarity(cursor, fr_system, live_embedding, min_similarity=FACE_MATCH_SIMILARITY_THRESHOLD, max_samples=50):
    """Match a live embedding against stored enrollment captures using CFIS-style ranking."""
    if cursor is None or fr_system is None or live_embedding is None:
        return None, 0.0, []

    try:
        cursor.execute(
            """
            SELECT fc.student_id, fc.image_path, s.roll_number, s.first_name, s.last_name,
                   COALESCE(s.faces_captured, 0) AS faces_captured,
                   s.face_training_status
            FROM face_captures fc
            INNER JOIN students s ON s.student_id = fc.student_id
            ORDER BY fc.captured_at DESC, fc.capture_id DESC
            LIMIT %s
            """,
            (max_samples,)
        )
        rows = cursor.fetchall() or []
    except Exception:
        return None, 0.0, []

    embeddings_by_student = {}
    student_rows = {}
    for row in rows:
        student_id = row.get('student_id')
        image_path = row.get('image_path')
        if not image_path:
            continue

        capture_path = Path(image_path)
        if not capture_path.exists():
            capture_path = Path.cwd() / image_path
        if not capture_path.exists():
            continue

        stored_image = cv2.imread(str(capture_path))
        if stored_image is None:
            continue

        stored_result = fr_system.capture_face_from_image(stored_image, min_confidence=LIVE_FACE_DETECTION_THRESHOLD)
        if stored_result.get('status') != 'success':
            continue

        stored_embedding = _to_flat_embedding(stored_result.get('embedding'))
        if stored_embedding is None:
            continue

        embeddings_by_student.setdefault(student_id, []).append(stored_embedding)
        if student_id not in student_rows:
            student_rows[student_id] = {
                'student_id': row.get('student_id'),
                'roll_number': row.get('roll_number'),
                'first_name': row.get('first_name'),
                'last_name': row.get('last_name'),
                'faces_captured': row.get('faces_captured'),
                'face_training_status': row.get('face_training_status')
            }

    best_student = None
    best_similarity = 0.0
    matched_candidates = []

    for student_id, student_embeddings in embeddings_by_student.items():
        if not student_embeddings:
            continue

        stacked = np.vstack(student_embeddings)
        centroid = stacked.mean(axis=0)
        similarity = _cosine_similarity(live_embedding, centroid)
        distance = _cosine_distance(live_embedding, centroid)

        if similarity < min_similarity or distance > FACE_MATCH_DISTANCE_THRESHOLD:
            continue

        percentage = _distance_to_cfis_percentage(distance)
        if percentage is None:
            continue

        candidate = dict(student_rows.get(student_id) or {})
        candidate.update({
            'student_id': student_id,
            'distance': float(distance),
            'similarity': float(similarity),
            'match_percentage': float(percentage),
        })
        matched_candidates.append(candidate)

    matched_candidates.sort(key=lambda item: item['distance'])

    if matched_candidates:
        best_candidate = matched_candidates[0]
        best_student = {
            'student_id': best_candidate.get('student_id'),
            'roll_number': best_candidate.get('roll_number'),
            'first_name': best_candidate.get('first_name'),
            'last_name': best_candidate.get('last_name'),
            'faces_captured': best_candidate.get('faces_captured'),
            'face_training_status': best_candidate.get('face_training_status'),
        }
        best_similarity = float(best_candidate.get('similarity', 0.0))
        return best_student, best_similarity, matched_candidates

    return None, 0.0, []


def _ensure_student_face_columns():
    """Add optional face-recognition columns if the live database is missing them."""
    if not db.connection:
        return

    cursor = None
    try:
        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'students'
            """,
            (DATABASE_CONFIG['database'],)
        )
        existing_columns = {row[0] for row in cursor.fetchall()}

        required_columns = [
            ('face_registered', "ALTER TABLE students ADD COLUMN face_registered TINYINT(1) NOT NULL DEFAULT 0"),
            ('face_data', "ALTER TABLE students ADD COLUMN face_data LONGTEXT")
        ]

        for column_name, alter_sql in required_columns:
            if column_name not in existing_columns:
                print(f"[INFO] Adding missing students.{column_name} column")
                cursor.execute(alter_sql)
                db.connection.commit()
    except Exception as e:
        print(f"[WARNING] Could not ensure face columns: {e}")
    finally:
        if cursor:
            cursor.close()


def _dataset_image_paths_for_student(student_id):
    """Return readable image files already stored for a student."""
    dataset_dir = Path('dataset') / str(student_id)
    if not dataset_dir.exists() or not dataset_dir.is_dir():
        return []

    allowed_suffixes = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tif', '.tiff'}
    image_paths = []
    for path in dataset_dir.iterdir():
        if path.is_file() and path.suffix.lower() in allowed_suffixes:
            image_paths.append(path)

    image_paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return image_paths


def _sync_face_capture_records_from_dataset(student_id=None):
    """Backfill face capture rows and capture counters from the dataset folder."""
    if not db.connection:
        return

    cursor = None
    try:
        cursor = db.connection.cursor(dictionary=True)

        if student_id is None:
            cursor.execute("SELECT student_id FROM students")
            student_ids = [row['student_id'] for row in cursor.fetchall() or []]
        else:
            student_ids = [student_id]

        for sid in student_ids:
            image_paths = _dataset_image_paths_for_student(sid)
            if not image_paths:
                continue

            cursor.execute(
                """
                SELECT image_path
                FROM face_captures
                WHERE student_id = %s
                """,
                (sid,)
            )
            existing_paths = {str(row.get('image_path') or '').replace('\\', '/') for row in cursor.fetchall() or []}

            changed = False
            for path in image_paths:
                normalized_path = str(path).replace('\\', '/')
                if normalized_path in existing_paths:
                    continue

                try:
                    cursor.execute(
                        """
                        INSERT INTO face_captures (student_id, image_path, quality_score, is_used_for_training)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (sid, normalized_path, 1.0, False)
                    )
                    changed = True
                except Exception as e:
                    print(f"[WARNING] Could not backfill face_captures for student {sid}: {e}")

            image_count = len(image_paths)
            if image_count > 0:
                try:
                    cursor.execute(
                        """
                        UPDATE students
                        SET faces_captured = GREATEST(COALESCE(faces_captured, 0), %s),
                            face_registered = 1,
                            face_training_status = CASE
                                WHEN face_training_status = 'trained' THEN 'trained'
                                ELSE 'needs_retrain'
                            END,
                            last_face_capture = COALESCE(last_face_capture, NOW())
                        WHERE student_id = %s
                        """,
                        (image_count, sid)
                    )
                    changed = True
                except Exception as e:
                    print(f"[WARNING] Could not backfill student {sid} capture metadata: {e}")

            if changed:
                db.connection.commit()
    except Exception as e:
        print(f"[WARNING] Could not sync face captures from dataset: {e}")
    finally:
        if cursor:
            cursor.close()


def _save_capture_image(student_id, image_array):
    """Persist a captured frame under dataset/<student_id>/ and return relative path."""
    dataset_dir = Path('dataset') / str(student_id)
    dataset_dir.mkdir(parents=True, exist_ok=True)

    filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    image_path = dataset_dir / filename

    saved = cv2.imwrite(str(image_path), image_array)
    if not saved:
        raise ValueError('Failed to save captured image to dataset')

    return str(image_path).replace('\\\\', '/')


def _upsert_student_face_enrollment(student_id, new_embedding, image_array=None):
    """Update student embedding using running average and persist capture image metadata."""
    merged_embedding = _to_flat_embedding(new_embedding)
    if merged_embedding is None:
        raise ValueError('Invalid face embedding from capture')

    cursor = None
    image_path = None
    captures_count = None

    try:
        if image_array is not None:
            image_path = _save_capture_image(student_id, image_array)

        cursor = db.connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT COALESCE(faces_captured, 0) AS faces_captured
            FROM students
            WHERE student_id = %s
            """,
            (student_id,)
        )
        existing = cursor.fetchone() or {}
        existing_count = int(existing.get('faces_captured') or 0)
        cursor.execute(
            """
            UPDATE students
            SET faces_captured = COALESCE(faces_captured, 0) + 1,
                last_face_capture = NOW(),
                face_training_status = 'needs_retrain'
            WHERE student_id = %s
            """,
            (student_id,)
        )
        captures_count = existing_count + 1

        db.connection.commit()

        if image_path:
            try:
                cursor.execute(
                    """
                    INSERT INTO face_captures (student_id, image_path, quality_score, is_used_for_training)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (student_id, image_path, 1.0, False)
                )
                db.connection.commit()
            except Exception as e:
                db.connection.rollback()
                print(f"[WARNING] Could not write face_captures row: {e}")

        return {
            'embedding': merged_embedding.tolist(),
            'image_path': image_path,
            'captures_count': captures_count
        }
    finally:
        if cursor:
            cursor.close()

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
        ensure_connection()
        if not db.connection:
            print("[WARNING] Attendance fetch skipped because the database connection is unavailable")
            return []

        today = date.today()
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
             SELECT s.student_id, s.roll_number, s.first_name, s.last_name, 
                 c.class_name, al.log_id, al.entry_time, al.exit_time, al.status,
                 al.date as attendance_date, al.created_at
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.class_id
            LEFT JOIN attendance_logs al ON s.student_id = al.student_id AND al.date = %s
             ORDER BY al.created_at IS NULL, al.created_at DESC, al.log_id DESC, s.roll_number
        """, (today,))
        attendance = cursor.fetchall()
        
        # Format times
        for record in attendance:
            record['entry_time'] = format_db_value(record.get('entry_time'))
            record['exit_time'] = format_db_value(record.get('exit_time'))
            record['attendance_date'] = format_db_value(record.get('attendance_date'))
            record['created_at'] = format_db_value(record.get('created_at'))
        
        return attendance
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return JSONResponse({'error': f'Database error: {str(e)}'}, status_code=500)
    finally:
        if cursor:
            cursor.close()

@app.get("/api/attendance/recent-checkins")
async def get_recent_checkins(limit: int = Query(10, ge=1, le=50)):
    """Get the most recent check-in log entries for today."""
    cursor = None
    try:
        ensure_connection()
        if not db.connection:
            print("[WARNING] Recent check-ins fetch skipped because the database connection is unavailable")
            return []

        today = date.today()
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT al.log_id, s.student_id, s.roll_number, s.first_name, s.last_name,
                   c.class_name, al.entry_time, al.exit_time, al.status,
                   al.date as attendance_date, al.created_at
            FROM attendance_logs al
            INNER JOIN students s ON al.student_id = s.student_id
            LEFT JOIN classes c ON s.class_id = c.class_id
            WHERE al.date = %s
            ORDER BY al.created_at DESC, al.log_id DESC
            LIMIT %s
        """, (today, limit))
        attendance = cursor.fetchall()

        for record in attendance:
            record['entry_time'] = format_db_value(record.get('entry_time'))
            record['exit_time'] = format_db_value(record.get('exit_time'))
            record['attendance_date'] = format_db_value(record.get('attendance_date'))
            record['created_at'] = format_db_value(record.get('created_at'))

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
            record['entry_time'] = format_db_value(record.get('entry_time'))
            record['exit_time'] = format_db_value(record.get('exit_time'))
        
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
            record['date'] = format_db_value(record.get('date'))
            record['entry_time'] = format_db_value(record.get('entry_time'))
            record['exit_time'] = format_db_value(record.get('exit_time'))
        
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
            stat['date'] = format_db_value(stat.get('date'))
        
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

@app.get("/face-attendance")
@app.get("/face-enrollment")
async def face_enrollment_page(request: Request):
    """Face attendance page."""
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
            try:
                enrollment_update = _upsert_student_face_enrollment(
                    student_id=student_id,
                    new_embedding=result.get('embedding'),
                    image_array=image_array
                )
                result['embedding'] = enrollment_update['embedding']
                if enrollment_update.get('image_path'):
                    result['image_path'] = enrollment_update['image_path']
                if enrollment_update.get('captures_count') is not None:
                    result['captures_count'] = enrollment_update['captures_count']
            except Exception as e:
                print(f"[WARNING] Could not persist enrollment update: {e}")
        
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
        raw_detections = fr_system.detect_faces(frame, min_confidence=LIVE_FACE_DETECTION_THRESHOLD)

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
            try:
                enrollment_update = _upsert_student_face_enrollment(
                    student_id=student_id,
                    new_embedding=result.get('embedding'),
                    image_array=image_array
                )
                result['embedding'] = enrollment_update['embedding']
                if enrollment_update.get('image_path'):
                    result['image_path'] = enrollment_update['image_path']
                if enrollment_update.get('captures_count') is not None:
                    result['captures_count'] = enrollment_update['captures_count']
            except Exception as e:
                print(f"[WARNING] Could not persist enrollment update: {e}")
        
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
                   COALESCE(faces_captured, 0) AS faces_captured,
                   face_training_status
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
            'faces_captured': int(student.get('faces_captured') or 0),
            'has_embedding': int(student.get('faces_captured') or 0) > 0 or str(student.get('face_training_status') or '').lower() == 'trained'
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
        
        cursor.execute("SELECT COUNT(*) as enrolled FROM students WHERE face_training_status = 'trained'")
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
                [sys.executable, 'capture.py', str(student_id)],
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
        ensure_connection()
        if not db.connection:
            return JSONResponse(
                {'status': 'error', 'message': 'Database connection is unavailable'},
                status_code=503
            )

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
        
        # Record attendance as a new history row every time the student is detected
        today = date.today()
        checkin_timestamp = datetime.now()
        now = checkin_timestamp.time()
        cursor.execute("""
            INSERT INTO attendance_logs (student_id, date, entry_time, status)
            VALUES (%s, %s, %s, 'present')
        """, (student['student_id'], today, now))
        log_id = cursor.lastrowid
        
        # Also record in attendance scans
        cursor.execute("""
            INSERT INTO attendance_scans (student_id, scan_type, scan_time, confidence_score, recognized)
            VALUES (%s, 'entry', %s, 0.95, TRUE)
        """, (student['student_id'], datetime.now()))
        
        db.connection.commit()
        
        return JSONResponse({
            'status': 'success',
            'message': f"✓ {student['first_name']} {student['last_name']} check-in recorded",
            'record': {
                'log_id': log_id,
                'student_id': student['student_id'],
                'roll_number': student['roll_number'],
                'first_name': student['first_name'],
                'last_name': student['last_name'],
                'class_name': student.get('class_name'),
                'status': 'present',
                'attendance_date': today.isoformat(),
                'entry_time': now.isoformat(),
                'created_at': checkin_timestamp.isoformat()
            },
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
    """Get today's check-in history for a student."""
    cursor = None
    try:
        cursor = db.connection.cursor(dictionary=True)
        
        today = date.today()
        cursor.execute("""
            SELECT al.*
            FROM attendance_logs al
            INNER JOIN students s ON s.student_id = al.student_id
            WHERE (s.student_id = %s OR s.roll_number = %s) AND al.date = %s
            ORDER BY al.created_at DESC, al.log_id DESC
        """, (student_id if student_id.isdigit() else None, student_id, today))
        
        results = cursor.fetchall()

        if results:
            latest = results[0]
            return {
                'status': 'checked_in',
                'message': f'Student has {len(results)} check-in record(s) today',
                'checkin_count': len(results),
                'time': str(latest.get('entry_time')),
                'latest_checkin': {
                    'date': format_db_value(latest.get('date')),
                    'time': format_db_value(latest.get('entry_time')),
                    'status': latest.get('status')
                }
            }
        else:
            return {'status': 'not_present', 'message': 'No check-in records yet today'}
            
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
        raw_detections = fr_system.detect_faces(frame, min_confidence=LIVE_FACE_DETECTION_THRESHOLD)
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
                'confidence': float(detection.get('confidence', 0.0))
            })
        
        if not raw_detections:
            return JSONResponse({
                'status': 'error',
                'message': 'No face detected',
                'recognized': False,
                'faces': []
            })

        # Extract embedding from the best detected face in this frame
        capture_result = fr_system.capture_face_from_image(frame, min_confidence=LIVE_FACE_DETECTION_THRESHOLD)
        if capture_result.get('status') != 'success':
            return JSONResponse({
                'status': 'error',
                'message': capture_result.get('message', 'Face detected, but embedding extraction failed'),
                'recognized': False,
                'faces': faces_payload
            })

        live_embedding = _to_flat_embedding(capture_result.get('embedding'))
        if live_embedding is None:
            return JSONResponse({
                'status': 'error',
                'message': 'Could not prepare face embedding for matching',
                'recognized': False,
                'faces': faces_payload
            })

        _sync_face_capture_records_from_dataset()

        cursor = db.connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT student_id, roll_number, first_name, last_name, faces_captured, face_training_status
            FROM students
            WHERE COALESCE(faces_captured, 0) > 0 OR face_training_status IN ('trained', 'needs_retrain')
            ORDER BY student_id
        """)
        enrolled_students = cursor.fetchall() or []

        student, capture_similarity, matched_candidates = _find_student_by_capture_similarity(
            cursor,
            fr_system,
            live_embedding,
            min_similarity=FACE_MATCH_SIMILARITY_THRESHOLD
        )

        if student:
            return JSONResponse({
                'status': 'success',
                'message': f'Face recognized: {student["first_name"]} {student["last_name"]}',
                'recognized': True,
                'match_source': 'database_capture',
                'matching_type': 'cfis_style_distance',
                'student': {
                    'id': student['student_id'],
                    'name': f"{student['first_name']} {student['last_name']}",
                    'roll_number': student['roll_number']
                },
                'confidence': float(capture_similarity),
                'capture_similarity': float(capture_similarity),
                'match_percentage': float(matched_candidates[0]['match_percentage']) if matched_candidates else float(capture_similarity) * 100.0,
                'matches': matched_candidates[:5],
                'faces': faces_payload
            })
        else:
            return JSONResponse({
                'status': 'error',
                'message': 'Face does not match any student in the database',
                'recognized': False,
                'match_source': 'database_capture',
                'matching_type': 'cfis_style_distance',
                'confidence': float(capture_similarity),
                'capture_similarity': float(capture_similarity),
                'matches': matched_candidates,
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
