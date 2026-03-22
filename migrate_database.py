"""
Database Migration - Add missing columns to students table
"""

import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='school_attendance'
    )
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute('DESCRIBE students')
    columns = cursor.fetchall()
    col_names = [col[0] for col in columns]
    
    print('Existing columns:', col_names)
    
    # Add missing columns if they don't exist
    if 'face_training_status' not in col_names:
        cursor.execute("ALTER TABLE students ADD COLUMN face_training_status ENUM('pending', 'trained', 'needs_retrain') DEFAULT 'pending'")
        print('[OK] Added face_training_status column')
    else:
        print('[SKIP] face_training_status column already exists')
    
    if 'faces_captured' not in col_names:
        cursor.execute('ALTER TABLE students ADD COLUMN faces_captured INT DEFAULT 0')
        print('[OK] Added faces_captured column')
    else:
        print('[SKIP] faces_captured column already exists')
    
    if 'last_face_capture' not in col_names:
        cursor.execute('ALTER TABLE students ADD COLUMN last_face_capture TIMESTAMP NULL')
        print('[OK] Added last_face_capture column')
    else:
        print('[SKIP] last_face_capture column already exists')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print('\n[SUCCESS] Database migration complete!')

except Exception as e:
    print(f'[ERROR] Migration failed: {e}')
