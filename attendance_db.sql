-- School Attendance Management System Database

CREATE DATABASE IF NOT EXISTS school_attendance;
USE school_attendance;

-- Teachers Table (Create before Classes)
CREATE TABLE IF NOT EXISTS teachers (
    teacher_id INT PRIMARY KEY AUTO_INCREMENT,
    employee_id VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Classes Table (Create before Students)
CREATE TABLE IF NOT EXISTS classes (
    class_id INT PRIMARY KEY AUTO_INCREMENT,
    class_name VARCHAR(50) NOT NULL,
    teacher_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
);

-- Students Table
CREATE TABLE IF NOT EXISTS students (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    roll_number VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    face_registered TINYINT(1) NOT NULL DEFAULT 0,
    face_data LONGTEXT,
    face_image_path VARCHAR(255),
    class_id INT,
    date_of_admission DATE,
    face_training_status ENUM('pending', 'trained', 'needs_retrain') DEFAULT 'pending',
    faces_captured INT DEFAULT 0,
    last_face_capture TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(class_id)
);

-- Parent/Guardian Contacts Table
CREATE TABLE IF NOT EXISTS parent_contacts (
    contact_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    parent_name VARCHAR(100),
    phone_number VARCHAR(20) NOT NULL,
    relationship VARCHAR(50),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- Attendance Log Table
CREATE TABLE IF NOT EXISTS attendance_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    date DATE NOT NULL,
    entry_time TIME,
    exit_time TIME,
    status ENUM('present', 'absent', 'late', 'leave') DEFAULT 'present',
    remarks VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
);

-- Attendance Scan Logs (Raw scan data)
CREATE TABLE IF NOT EXISTS attendance_scans (
    scan_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    scan_type ENUM('entry', 'exit') NOT NULL,
    scan_time DATETIME NOT NULL,
    confidence_score FLOAT,
    recognized BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    INDEX idx_student_time (student_id, scan_time)
);

-- SMS Notification Logs
CREATE TABLE IF NOT EXISTS sms_notifications (
    notification_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    parent_id INT,
    message TEXT,
    phone_number VARCHAR(20),
    status ENUM('pending', 'sent', 'failed') DEFAULT 'pending',
    attempt_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (parent_id) REFERENCES parent_contacts(contact_id)
);

-- Face Captures Table (Tracks individual face images captured during enrollment)
CREATE TABLE IF NOT EXISTS face_captures (
    capture_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quality_score FLOAT DEFAULT 0,
    is_used_for_training BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    INDEX idx_student_captures (student_id)
);

-- Training Sessions Table (Tracks model retraining)
CREATE TABLE IF NOT EXISTS training_sessions (
    session_id INT PRIMARY KEY AUTO_INCREMENT,
    status ENUM('started', 'completed', 'failed') DEFAULT 'started',
    students_processed INT DEFAULT 0,
    total_embeddings INT DEFAULT 0,
    training_duration FLOAT,
    model_accuracy FLOAT,
    error_message TEXT,
    triggered_by VARCHAR(50) DEFAULT 'scheduler',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_session_status (status)
);

-- Class Registration Table (Tracks student enrollments in classes with assigned teachers)
CREATE TABLE IF NOT EXISTS class_registrations (
    registration_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    class_id INT NOT NULL,
    teacher_id INT,
    registration_date DATE NOT NULL,
    status ENUM('active', 'inactive', 'completed') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_student_class (student_id, class_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE SET NULL,
    INDEX idx_class_registrations (class_id),
    INDEX idx_student_registrations (student_id),
    INDEX idx_teacher_registrations (teacher_id)
);

-- Create indexes for better query performance
CREATE INDEX idx_student_date ON attendance_logs(student_id, date);
CREATE INDEX idx_class_id ON students(class_id);
CREATE INDEX idx_teacher_id ON classes(teacher_id);
CREATE INDEX idx_scan_student_type ON attendance_scans(student_id, scan_type);
