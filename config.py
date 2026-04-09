# Configuration file for School Attendance System
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration (XAMPP MySQL)
# Credentials should be set via environment variables for security
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'school_attendance'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'autocommit': True,
    'use_unicode': True,
    'charset': 'utf8mb4'
}

# Facial Recognition Models
FACE_DETECTOR_PATH = 'Models'
FACE_EMBEDDING_MODEL = 'openface_nn4.small2.v1.t7'
RECOGNIZER_MODEL = 'output/recognizer.pickle'
LABEL_ENCODER = 'output/le.pickle'

# Recognition Confidence Threshold
# Lowered detection threshold to improve face detection in varied lighting/angles
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', 0.35))
FACE_MIN_WIDTH = int(os.getenv('FACE_MIN_WIDTH', 20))
FACE_MIN_HEIGHT = int(os.getenv('FACE_MIN_HEIGHT', 20))

# Image Upload Validation
IMAGE_VALIDATION = {
    'max_size_mb': int(os.getenv('IMAGE_MAX_SIZE_MB', 5)),
    'max_size_bytes': int(os.getenv('IMAGE_MAX_SIZE_MB', 5)) * 1024 * 1024,
    'allowed_formats': ['jpeg', 'jpg', 'png'],
    'min_width': int(os.getenv('IMAGE_MIN_WIDTH', 100)),
    'min_height': int(os.getenv('IMAGE_MIN_HEIGHT', 100)),
    'max_width': int(os.getenv('IMAGE_MAX_WIDTH', 4096)),
    'max_height': int(os.getenv('IMAGE_MAX_HEIGHT', 4096))
}

# API Configuration
API_CONFIG = {
    'max_results_per_page': int(os.getenv('MAX_RESULTS_PER_PAGE', 50)),
    'default_page_size': int(os.getenv('DEFAULT_PAGE_SIZE', 20)),
    'rate_limit_calls': int(os.getenv('RATE_LIMIT_CALLS', 100)),
    'rate_limit_period': int(os.getenv('RATE_LIMIT_PERIOD', 60)),  # seconds
}

# SMS Configuration (Twilio or similar service)
SMS_CONFIG = {
    'enabled': os.getenv('SMS_ENABLED', 'False').lower() == 'true',
    'provider': os.getenv('SMS_PROVIDER', 'twilio'),
    'account_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
    'auth_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
    'from_number': os.getenv('TWILIO_FROM_NUMBER', '')
}

# School Information
SCHOOL_INFO = {
    'name': os.getenv('SCHOOL_NAME', 'Your School Name'),
    'school_time_start': os.getenv('SCHOOL_TIME_START', '08:00'),
    'school_time_end': os.getenv('SCHOOL_TIME_END', '15:30'),
    'late_threshold_minutes': int(os.getenv('LATE_THRESHOLD_MINUTES', 15))
}

# Email Configuration (for PDF reports)
EMAIL_CONFIG = {
    'enabled': os.getenv('EMAIL_ENABLED', 'False').lower() == 'true',
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'sender_email': os.getenv('SENDER_EMAIL', ''),
    'sender_password': os.getenv('SENDER_PASSWORD', '')
}

# FastAPI Configuration
FASTAPI_CONFIG = {
    'host': os.getenv('FASTAPI_HOST', '127.0.0.1'),
    'port': int(os.getenv('FASTAPI_PORT', 5000)),
    'reload': os.getenv('FASTAPI_RELOAD', 'True').lower() == 'true',
    'debug': os.getenv('FASTAPI_DEBUG', 'True').lower() == 'true'
}
