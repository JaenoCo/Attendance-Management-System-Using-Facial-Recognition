"""
Database migration script to add face enrollment columns
Run this once to update the database schema
"""

import mysql.connector
from config import DATABASE_CONFIG

def migrate_database():
    """Add face enrollment columns to students table"""
    try:
        conn = mysql.connector.connect(
            host=DATABASE_CONFIG['host'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            database=DATABASE_CONFIG['database']
        )
        
        cursor = conn.cursor()
        
        print("[INFO] Starting database migration...")
        
        # Check if columns already exist
        cursor.execute(f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME='students' 
            AND TABLE_SCHEMA='{DATABASE_CONFIG['database']}'
            AND COLUMN_NAME IN ('face_registered', 'face_data')
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add face_registered column if it doesn't exist
        if 'face_registered' not in existing_columns:
            print("[INFO] Adding 'face_registered' column...")
            cursor.execute("""
                ALTER TABLE students 
                ADD COLUMN face_registered TINYINT DEFAULT 0
            """)
            print("[✓] Added 'face_registered' column")
        else:
            print("[INFO] 'face_registered' column already exists")
        
        # Add face_data column if it doesn't exist
        if 'face_data' not in existing_columns:
            print("[INFO] Adding 'face_data' column...")
            cursor.execute("""
                ALTER TABLE students 
                ADD COLUMN face_data LONGTEXT DEFAULT NULL COMMENT 'JSON encoded face embedding'
            """)
            print("[✓] Added 'face_data' column")
        else:
            print("[INFO] 'face_data' column already exists")
        
        conn.commit()
        print("\n[✓] Database migration completed successfully!")
        print("[INFO] Students table now has facial enrollment support")
        
        # Show updated schema
        cursor.execute(f"""
            DESCRIBE students
        """)
        
        print("\n[INFO] Updated students table schema:")
        print("-" * 80)
        for column_info in cursor.fetchall():
            print(f"  {column_info[0]:<20} {column_info[1]:<30} {column_info[3]:<10}")
        print("-" * 80)
        
        cursor.close()
        conn.close()
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("School Attendance System - Database Migration")
    print("=" * 80)
    print()
    
    if migrate_database():
        print("\n[SUCCESS] Database is ready for facial enrollment!")
    else:
        print("\n[FAILED] Migration did not complete. Check the errors above.")
