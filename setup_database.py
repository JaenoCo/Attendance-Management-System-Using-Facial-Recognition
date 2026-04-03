"""
Database Setup Script - Initialize MySQL database with schema
Run this ONCE to set up the school_attendance database
"""

import mysql.connector
from mysql.connector import Error

# Database connection without specifying database (to create it)
try:
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',  # Default XAMPP MySQL has no password
    )
    
    if connection.is_connected():
        cursor = connection.cursor()
        print("[INFO] Connected to MySQL server")
        
        # Read and execute the SQL schema file
        with open('attendance_db.sql', 'r', encoding='utf-8') as sql_file:
            sql_script = sql_file.read()
        
        # Split and execute each statement
        statements = sql_script.split(';')
        
        for statement in statements:
            statement = statement.strip()
            if statement:  # Skip empty statements
                try:
                    cursor.execute(statement)
                    print(f"[OK] Executed: {statement[:60]}...")
                except Error as e:
                    print(f"[WARNING] {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("\n[SUCCESS] Database initialization complete!")
        print("[INFO] You can now run the application")
        
except Error as e:
    print(f"[ERROR] Database setup failed: {e}")
    print("[HINT] Ensure MySQL is running on localhost")
