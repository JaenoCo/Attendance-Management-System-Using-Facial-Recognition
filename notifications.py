"""
SMS Notification Module for Parent/Guardian Alerts
Supports Twilio for sending SMS messages
"""

from config import SMS_CONFIG
from datetime import datetime
import requests

class SMSNotificationService:
    """Handle SMS notifications to parents/guardians"""
    
    def __init__(self):
        self.enabled = SMS_CONFIG['enabled']
        self.provider = SMS_CONFIG['provider']
        self.account_sid = SMS_CONFIG['account_sid']
        self.auth_token = SMS_CONFIG['auth_token']
        self.from_number = SMS_CONFIG['from_number']
    
    def send_attendance_notification(self, student_name, parent_phone, entry_time=None, exit_time=None):
        """Send attendance status notification to parent"""
        if not self.enabled:
            print("[INFO] SMS notifications disabled")
            return False
        
        if entry_time and not exit_time:
            message = f"Your child {student_name} has arrived at school at {entry_time.strftime('%H:%M')}. School ID: ATTEND-SYSTEM"
        elif exit_time and entry_time:
            message = f"Your child {student_name} has left school at {exit_time.strftime('%H:%M')}. School ID: ATTEND-SYSTEM"
        else:
            return False
        
        return self._send_sms(parent_phone, message)
    
    def send_late_arrival_alert(self, student_name, parent_phone, arrival_time, LATE_THRESHOLD):
        """Send alert if student arrives late"""
        message = f"ALERT: {student_name} marked as LATE arrival at {arrival_time.strftime('%H:%M')} (School starts at 08:00). School ID: ATTEND-SYSTEM"
        return self._send_sms(parent_phone, message)
    
    def send_absence_alert(self, student_name, parent_phone, date):
        """Send alert if student is absent"""
        message = f"ALERT: {student_name} is marked ABSENT on {date.strftime('%d-%m-%Y')}. School ID: ATTEND-SYSTEM"
        return self._send_sms(parent_phone, message)
    
    def _send_sms(self, phone_number, message):
        """Send SMS via Twilio"""
        if not self.enabled:
            return False
        
        try:
            if self.provider == 'twilio':
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
                payload = {
                    "From": self.from_number,
                    "To": phone_number,
                    "Body": message
                }
                auth = (self.account_sid, self.auth_token)
                response = requests.post(url, data=payload, auth=auth)
                
                if response.status_code == 201:
                    print(f"[INFO] SMS sent to {phone_number}")
                    return True
                else:
                    print(f"[ERROR] Failed to send SMS: {response.text}")
                    return False
            
        except Exception as e:
            print(f"[ERROR] Exception while sending SMS: {e}")
            return False
    
    def send_bulk_notifications(self, notifications_list):
        """Send multiple notifications"""
        results = []
        for notification in notifications_list:
            result = self._send_sms(notification['phone'], notification['message'])
            results.append(result)
        return results

class AttendanceAlerts:
    """Handle attendance-based alerts"""
    
    def __init__(self, db_connection, sms_service):
        self.db = db_connection
        self.sms = sms_service
    
    def check_and_alert_late_arrival(self, student_id, arrival_time, school_start_time='08:00'):
        """Check if student is late and send alert"""
        student = self.db.get_student_by_id(student_id)
        contacts = self.db.get_student_contacts(student_id)
        
        if not student or not contacts:
            return False
        
        # Parse school start time
        try:
            start_hour, start_min = map(int, school_start_time.split(':'))
            arrival_hour, arrival_min = arrival_time.hour, arrival_time.minute
            
            # Calculate minutes after school start
            school_start_mins = start_hour * 60 + start_min
            arrival_mins = arrival_hour * 60 + arrival_min
            
            if arrival_mins > school_start_mins:
                # Student is late
                for contact in contacts:
                    message = f"ALERT: {student['first_name']} {student['last_name']} marked as LATE arrival at {arrival_time.strftime('%H:%M')}. School starts at {school_start_time}."
                    self.sms._send_sms(contact['phone_number'], message)
                return True
        except Exception as e:
            print(f"[ERROR] Error checking late arrival: {e}")
        
        return False
