# Configuration file for School Attendance System

# Database Configuration (XAMPP MySQL)
DATABASE_CONFIG = {
    'host': 'localhost',
    'user': 'root',           # Default XAMPP MySQL user
    'password': '',           # Default XAMPP has no password
    'database': 'school_attendance'
}

# Facial Recognition Models
FACE_DETECTOR_PATH = 'Models'
FACE_EMBEDDING_MODEL = 'openface_nn4.small2.v1.t7'
RECOGNIZER_MODEL = 'output/recognizer.pickle'
LABEL_ENCODER = 'output/le.pickle'

# Recognition Confidence Threshold
# Lowered detection threshold to improve face detection in varied lighting/angles
CONFIDENCE_THRESHOLD = 0.35
FACE_MIN_WIDTH = 20
FACE_MIN_HEIGHT = 20

# SMS Configuration (Twilio or similar service)
SMS_CONFIG = {
    'enabled': True,
    'provider': 'twilio',  # 'twilio' or 'aws_sns'
    'account_sid': 'YOUR_TWILIO_ACCOUNT_SID',
    'auth_token': 'YOUR_TWILIO_AUTH_TOKEN',
    'from_number': '+1234567890'  # Your Twilio phone number
}

# School Information
SCHOOL_INFO = {
    'name': 'Your School Name',
    'school_time_start': '08:00',  # HH:MM format
    'school_time_end': '15:30',
    'late_threshold_minutes': 15  # Minutes after school start to mark as late
}

# Email Configuration (for PDF reports)
EMAIL_CONFIG = {
    'enabled': False,
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'your_email@gmail.com',
    'sender_password': 'your_app_password'
}

# FastAPI Configuration
FASTAPI_CONFIG = {
    'host': '127.0.0.1',
    'port': 5000,
    'reload': True,
    'debug': True
}
