import sqlite3
import asyncio
from datetime import datetime
from typing import List, Tuple, Optional

class AttendanceDB:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        """Initialize the database with attendance table"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def add_attendance(self, user_id: int, name: str, latitude: float, longitude: float) -> bool:
        """Add attendance record"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Check if user already marked attendance today
            cursor.execute(
                "SELECT id FROM attendance WHERE user_id = ? AND date = ?",
                (user_id, today)
            )
            
            if cursor.fetchone():
                conn.close()
                return False  # Already marked attendance today
            
            cursor.execute(
                "INSERT INTO attendance (user_id, name, date, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
                (user_id, name, today, latitude, longitude)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Database error: {e}")
            return False
    
    async def get_today_attendance(self) -> List[Tuple]:
        """Get today's attendance records"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute(
                "SELECT name, latitude, longitude, timestamp FROM attendance WHERE date = ? ORDER BY timestamp",
                (today,)
            )
            
            records = cursor.fetchall()
            conn.close()
            return records
            
        except Exception as e:
            print(f"Database error: {e}")
            return []
