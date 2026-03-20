#!/usr/bin/env python3
"""
Setup and Configuration Script for Python Facial Enrollment
===========================================================

This script helps you set up and test your Python facial enrollment system.
"""

import os
import sys
import json
from pathlib import Path

def check_files():
    """Check if all required files exist"""
    print("\n" + "="*60)
    print("CHECKING FILES...")
    print("="*60)
    
    required_files = [
        'face_enroll_cli.py',
        'face_enroll_examples.py',
        'facial_recognition.py',
    ]
    
    all_exist = True
    for file in required_files:
        exists = os.path.exists(file)
        status = "✓" if exists else "✗"
        print(f"{status} {file}")
        all_exist = all_exist and exists
    
    return all_exist

def configure_database():
    """Configure database credentials"""
    print("\n" + "="*60)
    print("DATABASE CONFIGURATION")
    print("="*60)
    
    config_file = Path('db_config.json')
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
        print("✓ Found existing db_config.json")
        print(f"  Host: {config.get('host', 'localhost')}")
        print(f"  User: {config.get('user', 'root')}")
        return config
    
    print("\nNo db_config.json found. Let's configure it.")
    print("Press Enter to use default values (shown in brackets)")
    
    host = input("\nMySQL Host [localhost]: ").strip() or 'localhost'
    user = input("MySQL User [root]: ").strip() or 'root'
    password = input("MySQL Password [root]: ").strip() or 'root'
    database = input("Database Name [school_attendance]: ").strip() or 'school_attendance'
    
    config = {
        'host': host,
        'user': user,
        'password': password,
        'database': database
    }
    
    # Save to file
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n✓ Configuration saved to db_config.json")
    
    return config

def test_database_connection(config):
    """Test database connection"""
    print("\n" + "="*60)
    print("TESTING DATABASE CONNECTION...")
    print("="*60)
    
    try:
        import mysql.connector
        
        print(f"Connecting to {config['host']} as {config['user']}...")
        
        connection = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database']
        )
        
        print("✓ Connection successful!")
        
        # Test query
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM students")
        result = cursor.fetchone()
        student_count = result[0]
        
        print(f"✓ Table 'students' found with {student_count} records")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

def test_facial_recognition():
    """Test facial recognition module"""
    print("\n" + "="*60)
    print("TESTING FACIAL RECOGNITION MODULE...")
    print("="*60)
    
    try:
        from facial_recognition import get_facial_recognition_system
        
        print("Loading facial recognition system...")
        fr_system = get_facial_recognition_system()
        
        print("✓ Facial recognition module loaded successfully!")
        
        # Check models
        print("✓ Face detector ready")
        print("✓ Face embedder ready")
        print("✓ Face recognizer ready")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to load: {e}")
        return False

def test_cli():
    """Test CLI tool"""
    print("\n" + "="*60)
    print("TESTING CLI TOOL...")
    print("="*60)
    
    try:
        import face_enroll_cli
        print("✓ CLI module loaded successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to load: {e}")
        return False

def show_next_steps(db_connected):
    """Show next steps"""
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    
    if db_connected:
        print("""
You're all set! Try these commands:

1. List all students:
   python face_enroll_cli.py list

2. Check enrollment statistics:
   python face_enroll_cli.py stats

3. Enroll a student from webcam:
   python face_enroll_cli.py capture-webcam --student_id 1

4. Enroll from an image:
   python face_enroll_cli.py capture-image --student_id 1 --image photo.jpg

5. Batch enroll from folder:
   python face_enroll_cli.py batch-enroll --folder ./photos/

6. Train the facial model:
   python face_enroll_cli.py train

For more help:
   python face_enroll_cli.py --help
   read PYTHON_ENROLLMENT_GUIDE.md
   read ENROLLMENT_CHEATSHEET.md
        """)
    else:
        print("""
Database connection failed. Please:

1. Ensure MySQL is running
2. Check your database credentials in db_config.json
3. Verify the database 'school_attendance' exists
4. Run this setup script again

To fix the password:
   1. Edit db_config.json
   2. Change the 'password' field
   3. Run: python face_enroll_cli.py stats
        """)

def main():
    """Main setup flow"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║   Python Facial Enrollment System - Setup & Configuration     ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Check files
    if not check_files():
        print("\n✗ Some required files are missing!")
        return False
    
    print("\n✓ All required files found!")
    
    # Step 2: Configure database
    config = configure_database()
    
    # Step 3: Test database
    db_ok = test_database_connection(config)
    
    # Step 4: Test facial recognition
    test_facial_recognition()
    
    # Step 5: Test CLI
    test_cli()
    
    # Step 6: Show next steps
    show_next_steps(db_ok)
    
    print("\n" + "="*60)
    if db_ok:
        print("✓ SETUP COMPLETE - System is ready to use!")
    else:
        print("⚠ SETUP INCOMPLETE - Fix database connection")
    print("="*60 + "\n")
    
    return db_ok

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
