"""
Database Connection Module
Handles MySQL database operations for the attendance system
with connection pooling, retry logic, and error handling
"""

import mysql.connector
from mysql.connector import Error, pooling
from datetime import datetime, date, timedelta
import json
import logging
import time

# Setup logging
logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Handle MySQL database connections and operations with connection pooling"""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self, host='localhost', user='root', password='', database='school_attendance', pool_name='attendance_pool'):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.pool_name = pool_name
        self.connection = None
        self.pool = None
        self._last_connection_attempt = 0
    
    def connect(self):
        """Establish database connection with connection pooling"""
        try:
            # Try to reuse existing connection
            if self.connection and self.connection.is_connected():
                return True
            
            # Create connection pool if not exists
            if self.pool is None:
                try:
                    self.pool = pooling.MySQLConnectionPool(
                        pool_name=self.pool_name,
                        pool_size=5,  # Default pool size
                        pool_reset_session=True,
                        host=self.host,
                        user=self.user,
                        password=self.password,
                        database=self.database,
                        autocommit=True,
                        use_unicode=True,
                        charset='utf8mb4'
                    )
                    logger.info(f"[INFO] Connection pool '{self.pool_name}' created")
                except Error as e:
                    logger.error(f"[ERROR] Failed to create connection pool: {e}")
                    if 'already exists' not in str(e):
                        self.pool = None
                        raise
            
            # Get connection from pool with retry logic
            for attempt in range(self.MAX_RETRIES):
                try:
                    self.connection = self.pool.get_connection()
                    
                    if self.connection.is_connected():
                        logger.info(f"[INFO] Connected to {self.database} database (attempt {attempt + 1})")
                        return True
                        
                except Error as e:
                    logger.warning(f"[WARNING] Connection attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY * (attempt + 1))  # Exponential backoff
                    else:
                        raise
            
            return False
            
        except Error as e:
            logger.error(f"[ERROR] Database connection failed after {self.MAX_RETRIES} retries: {e}")
            self.connection = None
            return False
    
    def _ensure_connection(self):
        """Ensure database connection is active, reconnect if needed"""
        try:
            if self.connection is None or not self.connection.is_connected():
                return self.connect()
            return True
        except Error as e:
            logger.error(f"[ERROR] Connection check failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("[INFO] Database connection closed")
    
    def get_student_by_name(self, name):
        """Fetch student by name with connection retry"""
        cursor = None
        try:
            if not self._ensure_connection():
                return None
                
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM students WHERE CONCAT(first_name, ' ', last_name) LIKE %s OR roll_number = %s"
            cursor.execute(query, (f"%{name}%", name))
            result = cursor.fetchone()
            return result
        except Error as e:
            logger.error(f"[ERROR] Error fetching student: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def get_student_by_id(self, student_id):
        """Fetch student by ID with connection retry"""
        cursor = None
        try:
            if not self._ensure_connection():
                return None
                
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM students WHERE student_id = %s"
            cursor.execute(query, (student_id,))
            result = cursor.fetchone()
            return result
        except Error as e:
            logger.error(f"[ERROR] Error fetching student: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def log_attendance_scan(self, student_id, scan_type, confidence_score=None):
        """Log facial recognition scan with connection retry"""
        cursor = None
        try:
            if not self._ensure_connection():
                logger.error("Could not establish database connection for logging scan")
                return False
            
            cursor = self.connection.cursor()
            current_time = datetime.now()
            query = """
                INSERT INTO attendance_scans 
                (student_id, scan_type, scan_time, confidence_score, recognized)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (student_id, scan_type, current_time, confidence_score, True))
            self.connection.commit()
            return True
        except Error as e:
            logger.error(f"[ERROR] Error logging scan: {e}")
            if self.connection:
                try:
                    self.connection.rollback()
                except:
                    pass
            return False
        finally:
            if cursor:
                cursor.close()
    
    def get_today_attendance(self, student_id):
        """Get today's attendance record for a student with connection retry"""
        cursor = None
        try:
            if not self._ensure_connection():
                return None
            
            cursor = self.connection.cursor(dictionary=True)
            today = date.today()
            query = "SELECT * FROM attendance_logs WHERE student_id = %s AND date = %s"
            cursor.execute(query, (student_id, today))
            result = cursor.fetchone()
            return result
        except Error as e:
            logger.error(f"[ERROR] Error fetching attendance: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def mark_attendance(self, student_id, status='present'):
        """Mark student attendance with connection retry and error handling"""
        cursor = None
        try:
            if not self._ensure_connection():
                return {'status': 'error', 'message': 'Database connection failed'}
            
            cursor = self.connection.cursor()
            today = date.today()
            now = datetime.now().time()
            
            query = """
                INSERT INTO attendance_logs 
                (student_id, date, entry_time, status)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (student_id, today, now, status))
            self.connection.commit()
            
            logger.info(f"Attendance marked for student {student_id}: {status} at {now}")
            return {'status': 'success', 'time': str(now)}
        except Error as e:
            logger.error(f"[ERROR] Error marking attendance: {e}")
            if self.connection:
                try:
                    self.connection.rollback()
                except:
                    pass
            return {'status': 'error', 'message': str(e)}
        finally:
            if cursor:
                cursor.close()
    
    def get_class_attendance(self, class_id, target_date=None, page=1, page_size=50):
        """Get attendance for all students in a class with pagination"""
        cursor = None
        try:
            if not self._ensure_connection():
                return {'data': [], 'total': 0, 'page': page, 'page_size': page_size}
            
            cursor = self.connection.cursor(dictionary=True)
            if target_date is None:
                target_date = date.today()
            
            # Calculate offset for pagination
            offset = (page - 1) * page_size
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM students WHERE class_id = %s"
            cursor.execute(count_query, (class_id,))
            total = cursor.fetchone()['total']
            
            # Get paginated results
            query = """
                SELECT s.student_id, s.roll_number, s.first_name, s.last_name, 
                       c.class_name, al.entry_time, al.exit_time, al.status
                FROM students s
                LEFT JOIN classes c ON s.class_id = c.class_id
                LEFT JOIN attendance_logs al ON s.student_id = al.student_id AND al.date = %s
                WHERE s.class_id = %s 
                ORDER BY s.roll_number
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (target_date, class_id, page_size, offset))
            results = cursor.fetchall()
            
            return {
                'data': results,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        except Error as e:
            logger.error(f"[ERROR] Error getting class attendance: {e}")
            return {'data': [], 'total': 0, 'page': page, 'page_size': page_size}
        finally:
            if cursor:
                cursor.close()
    
    def get_attendance_report(self, student_id, start_date=None, end_date=None, page=1, page_size=30):
        """Get attendance report for a student in a date range with pagination"""
        cursor = None
        try:
            if not self._ensure_connection():
                return {'data': [], 'total': 0, 'page': page, 'page_size': page_size}
            
            cursor = self.connection.cursor(dictionary=True)
            if start_date is None:
                start_date = date.today() - timedelta(days=30)
            if end_date is None:
                end_date = date.today()
            
            # Calculate offset for pagination
            offset = (page - 1) * page_size
            
            # Get total count
            count_query = """
                SELECT COUNT(*) as total
                FROM students s
                LEFT JOIN attendance_logs al ON s.student_id = al.student_id
                WHERE s.student_id = %s AND (al.date BETWEEN %s AND %s OR al.date IS NULL)
            """
            cursor.execute(count_query, (student_id, start_date, end_date))
            total = cursor.fetchone()['total']
            
            # Get paginated results
            query = """
                SELECT s.student_id, s.roll_number, s.first_name, s.last_name,
                       al.date, al.entry_time, al.exit_time, al.status
                FROM students s
                LEFT JOIN attendance_logs al ON s.student_id = al.student_id
                WHERE s.student_id = %s AND (al.date BETWEEN %s AND %s OR al.date IS NULL)
                ORDER BY al.date DESC, al.entry_time DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (student_id, start_date, end_date, page_size, offset))
            results = cursor.fetchall()
            
            return {
                'data': results,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        except Error as e:
            logger.error(f"[ERROR] Error getting attendance report: {e}")
            return {'data': [], 'total': 0, 'page': page, 'page_size': page_size}
        finally:
            if cursor:
                cursor.close()
