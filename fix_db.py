"""
Simple database fix - add missing columns to students table
"""
import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', password='', database='school_attendance')
cursor = conn.cursor()

# Get all columns first
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='students' AND TABLE_SCHEMA='school_attendance'")
existing_cols = [row[0] for row in cursor.fetchall()]
print(f"Existing columns: {existing_cols}")

# Add missing columns
if 'face_training_status' not in existing_cols:
    print("Adding face_training_status...")
    cursor.execute("ALTER TABLE students ADD face_training_status VARCHAR(20) DEFAULT 'pending'")
    conn.commit()
    print("✓ Added face_training_status")

if 'faces_captured' not in existing_cols:
    print("Adding faces_captured...")
    cursor.execute("ALTER TABLE students ADD faces_captured INT DEFAULT 0")
    conn.commit()
    print("✓ Added faces_captured")

if 'last_face_capture' not in existing_cols:
    print("Adding last_face_capture...")
    cursor.execute("ALTER TABLE students ADD last_face_capture TIMESTAMP NULL DEFAULT NULL")
    conn.commit()
    print("✓ Added last_face_capture")

if 'face_registered' not in existing_cols:
    print("Adding face_registered...")
    cursor.execute("ALTER TABLE students ADD face_registered TINYINT(1) NOT NULL DEFAULT 0")
    conn.commit()
    print("✓ Added face_registered")

if 'face_data' not in existing_cols:
    print("Adding face_data...")
    cursor.execute("ALTER TABLE students ADD face_data LONGTEXT")
    conn.commit()
    print("✓ Added face_data")

cursor.close()
conn.close()
print("\n✓ Database fix complete!")
