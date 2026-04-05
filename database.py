"""
Database Connection Module
Handles MySQL database operations for the attendance system
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime, date, timedelta
import json

class DatabaseConnection:
    """Handle MySQL database connections and operations"""
    
    def __init__(self, host='localhost', user='root', password='', database='school_attendance'):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.connection.is_connected():
                print(f"[INFO] Connected to {self.database} database")
                return True
        except Error as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("[INFO] Database connection closed")
    
    def get_student_by_name(self, name):
        """Fetch student by name"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM students WHERE CONCAT(first_name, ' ', last_name) LIKE %s OR roll_number = %s"
            cursor.execute(query, (f"%{name}%", name))
            result = cursor.fetchone()
            return result
        except Error as e:
            print(f"[ERROR] Error fetching student: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def get_student_by_id(self, student_id):
        """Fetch student by ID"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM students WHERE student_id = %s"
            cursor.execute(query, (student_id,))
            result = cursor.fetchone()
            return result
        except Error as e:
            print(f"[ERROR] Error fetching student: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def log_attendance_scan(self, student_id, scan_type, confidence_score=None):
        """Log facial recognition scan"""
        cursor = None
        try:
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
            print(f"[ERROR] Error logging scan: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
    
    def get_today_attendance(self, student_id):
        """Get today's attendance record for a student"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            today = date.today()
            query = "SELECT * FROM attendance_logs WHERE student_id = %s AND date = %s"
            cursor.execute(query, (student_id, today))
            result = cursor.fetchone()
            return result
        except Error as e:
            print(f"[ERROR] Error fetching attendance: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def mark_attendance(self, student_id, status='present'):
        """Mark student attendance"""
        cursor = None
        try:
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
            
            return {'status': 'success', 'time': str(now)}
        except Error as e:
            print(f"[ERROR] Error marking attendance: {e}")
            return {'status': 'error', 'message': str(e)}
        finally:
            if cursor:
                cursor.close()
    
    def get_class_attendance(self, class_id, target_date=None):
        """Get attendance for all students in a class"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            if target_date is None:
                target_date = date.today()
            
            query = """
                SELECT s.student_id, s.roll_number, s.first_name, s.last_name, 
                       c.class_name, al.entry_time, al.exit_time, al.status
                FROM students s
                LEFT JOIN classes c ON s.class_id = c.class_id
                LEFT JOIN attendance_logs al ON s.student_id = al.student_id AND al.date = %s
                WHERE s.class_id = %s ORDER BY s.roll_number
            """
            cursor.execute(query, (target_date, class_id))
            results = cursor.fetchall()
            return results
        except Error as e:
            print(f"[ERROR] Error getting class attendance: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def get_attendance_report(self, student_id, start_date=None, end_date=None):
        """Get attendance report for a student in a date range"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            if start_date is None:
                start_date = date.today() - timedelta(days=30)
            if end_date is None:
                end_date = date.today()
            
            query = """
                SELECT s.student_id, s.roll_number, s.first_name, s.last_name,
                       al.date, al.entry_time, al.exit_time, al.status
                FROM students s
                LEFT JOIN attendance_logs al ON s.student_id = al.student_id
                WHERE s.student_id = %s AND al.date BETWEEN %s AND %s
                ORDER BY al.date DESC
            """
            cursor.execute(query, (student_id, start_date, end_date))
            results = cursor.fetchall()
            return results
        except Error as e:
            print(f"[ERROR] Error getting attendance report: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
