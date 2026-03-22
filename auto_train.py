"""
Automated Face Recognition Model Training Script
Runs extract_embeddings.py and training_model.py sequentially
Logs results to database for monitoring
"""

import subprocess
import sys
import os
import time
import pickle
from datetime import datetime
from database import DatabaseConnection
from config import DATABASE_CONFIG

class AutoTrainer:
    def __init__(self):
        self.db = DatabaseConnection(
            host=DATABASE_CONFIG['host'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            database=DATABASE_CONFIG['database']
        )
        self.session_id = None
        self.start_time = None
        self.error_message = None
        
    def log_session(self, status, error=None):
        """Log training session to database"""
        try:
            if not self.db.connection or not self.db.connection.is_connected():
                self.db.connect()
            
            cursor = self.db.connection.cursor()
            
            duration = None
            if self.start_time and status == 'completed':
                duration = time.time() - self.start_time
            
            if self.session_id is None:
                # Insert new session
                query = """
                    INSERT INTO training_sessions 
                    (status, triggered_by, started_at, error_message)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(query, (status, 'scheduler', datetime.now(), error))
                self.db.connection.commit()
                self.session_id = cursor.lastrowid
                print(f"[INFO] Training session {self.session_id} created")
            else:
                # Update existing session
                query = """
                    UPDATE training_sessions 
                    SET status = %s, completed_at = %s, training_duration = %s, error_message = %s
                    WHERE session_id = %s
                """
                completed_at = datetime.now() if status == 'completed' else None
                cursor.execute(query, (status, completed_at, duration, error, self.session_id))
                self.db.connection.commit()
                print(f"[INFO] Training session {self.session_id} updated to {status}")
                
            cursor.close()
        except Exception as e:
            print(f"[ERROR] Failed to log session: {e}")
    
    def extract_embeddings(self):
        """Run extract_embeddings.py with default arguments"""
        print("[INFO] Starting face embedding extraction...")
        try:
            cmd = [sys.executable, 'extract_embeddings.py']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                print(f"[ERROR] Embedding extraction failed: {error_msg}")
                self.error_message = f"Extraction failed: {error_msg[:500]}"
                return False
            
            print("[INFO] ✓ Face embeddings extracted successfully")
            print(result.stdout)
            return True
            
        except subprocess.TimeoutExpired:
            error_msg = "Embedding extraction timed out (5 minutes)"
            print(f"[ERROR] {error_msg}")
            self.error_message = error_msg
            return False
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Embedding extraction error: {error_msg}")
            self.error_message = error_msg
            return False
    
    def train_model(self):
        """Run training_model.py with default arguments"""
        print("[INFO] Starting model training...")
        try:
            cmd = [sys.executable, 'training_model.py']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                print(f"[ERROR] Model training failed: {error_msg}")
                self.error_message = f"Training failed: {error_msg[:500]}"
                return False
            
            print("[INFO] ✓ Model trained successfully")
            print(result.stdout)
            return True
            
        except subprocess.TimeoutExpired:
            error_msg = "Model training timed out (5 minutes)"
            print(f"[ERROR] {error_msg}")
            self.error_message = error_msg
            return False
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Model training error: {error_msg}")
            self.error_message = error_msg
            return False
    
    def update_student_training_status(self):
        """Mark all students as trained if embeddings exist"""
        try:
            if not os.path.exists('output/embeddings.pickle'):
                print("[WARN] Embeddings file not found, skipping student status update")
                return
            
            if not self.db.connection or not self.db.connection.is_connected():
                self.db.connect()
            
            cursor = self.db.connection.cursor()
            
            # Update all students with faces to 'trained' status
            query = """
                UPDATE students 
                SET face_training_status = 'trained'
                WHERE face_training_status = 'pending' OR face_training_status = 'needs_retrain'
            """
            cursor.execute(query)
            self.db.connection.commit()
            
            print(f"[INFO] ✓ Updated student training status in database")
            cursor.close()
            
        except Exception as e:
            print(f"[ERROR] Failed to update student status: {e}")
    
    def run(self):
        """Execute full training pipeline"""
        print("\n" + "="*60)
        print("AUTOMATED FACE RECOGNITION MODEL TRAINING")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        self.start_time = time.time()
        self.log_session('started')
        
        try:
            # Step 1: Extract embeddings
            if not self.extract_embeddings():
                self.log_session('failed', self.error_message)
                return False
            
            # Step 2: Train model
            if not self.train_model():
                self.log_session('failed', self.error_message)
                return False
            
            # Step 3: Update student status
            self.update_student_training_status()
            
            # Success
            print("\n" + "="*60)
            print("✓ TRAINING PIPELINE COMPLETED SUCCESSFULLY")
            print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Duration: {time.time() - self.start_time:.2f} seconds")
            print("="*60)
            
            self.log_session('completed')
            self.db.disconnect()
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n[ERROR] Unexpected error in training pipeline: {error_msg}")
            self.log_session('failed', error_msg)
            self.db.disconnect()
            return False


if __name__ == '__main__':
    trainer = AutoTrainer()
    success = trainer.run()
    sys.exit(0 if success else 1)
