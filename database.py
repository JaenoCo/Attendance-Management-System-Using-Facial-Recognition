import mysql.connector
from mysql.connector import Error
from datetime import datetime, date
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
    
    def update_or_create_attendance(self, student_id, scan_type):
        """Update attendance log with entry/exit times"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            today = date.today()
            current_time = datetime.now().time()
            
            # Check if attendance exists for today
            query = "SELECT * FROM attendance_logs WHERE student_id = %s AND date = %s"
            cursor.execute(query, (student_id, today))
            existing = cursor.fetchone()
            
            if existing:
                if scan_type == 'entry':
                    update_query = "UPDATE attendance_logs SET entry_time = %s WHERE student_id = %s AND date = %s"
                else:  # exit
                    update_query = "UPDATE attendance_logs SET exit_time = %s WHERE student_id = %s AND date = %s"
                cursor.execute(update_query, (current_time, student_id, today))
            else:
                # Create new attendance record
                if scan_type == 'entry':
                    insert_query = """
                        INSERT INTO attendance_logs (student_id, date, entry_time, status)
                        VALUES (%s, %s, %s, 'present')
                    """
                    cursor.execute(insert_query, (student_id, today, current_time))
                else:
                    insert_query = """
                        INSERT INTO attendance_logs (student_id, date, exit_time, status)
                        VALUES (%s, %s, %s, 'present')
                    """
                    cursor.execute(insert_query, (student_id, today, current_time))
            
            self.connection.commit()
            return True
        except Error as e:
            print(f"[ERROR] Error updating attendance: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
    
    def get_student_contacts(self, student_id):
        """Get parent/guardian contact info"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM parent_contacts WHERE student_id = %s"
            cursor.execute(query, (student_id,))
            results = cursor.fetchall()
            return results
        except Error as e:
            print(f"[ERROR] Error fetching contacts: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def log_sms_notification(self, student_id, parent_id, message, phone_number):
        """Log SMS notification"""
        cursor = None
        try:
            cursor = self.connection.cursor()
            query = """
                INSERT INTO sms_notifications 
                (student_id, parent_id, message, phone_number, status)
                VALUES (%s, %s, %s, %s, 'pending')
            """
            cursor.execute(query, (student_id, parent_id, message, phone_number))
            self.connection.commit()
            return True
        except Error as e:
            print(f"[ERROR] Error logging SMS: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
    
    def get_attendance_report(self, student_id, start_date=None, end_date=None):
        """Get attendance report for a student"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            if start_date and end_date:
                query = """
                    SELECT * FROM attendance_logs 
                    WHERE student_id = %s AND date BETWEEN %s AND %s
                    ORDER BY date DESC
                """
                cursor.execute(query, (student_id, start_date, end_date))
            else:
                query = """
                    SELECT * FROM attendance_logs 
                    WHERE student_id = %s
                    ORDER BY date DESC
                """
                cursor.execute(query, (student_id,))
            results = cursor.fetchall()
            return results
        except Error as e:
            print(f"[ERROR] Error fetching report: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def get_class_attendance(self, class_id, date):
        """Get all students' attendance for a class on a specific date"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT s.student_id, s.roll_number, s.first_name, s.last_name,
                       al.entry_time, al.exit_time, al.status
                FROM students s
                LEFT JOIN attendance_logs al ON s.student_id = al.student_id AND al.date = %s
                WHERE s.class_id = %s
                ORDER BY s.roll_number
            """
            cursor.execute(query, (date, class_id))
            results = cursor.fetchall()
            return results
        except Error as e:
            print(f"[ERROR] Error fetching class attendance: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
