import sqlite3
import os
import sys
from datetime import datetime

if getattr(sys, 'frozen', False):
    # If running as PyInstaller executable, put DB next to the .exe
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(__file__)

DB_NAME = os.path.join(base_dir, "worktime.db")

def get_connection():
    try:
        # Check if we can write to the base directory
        test_file = os.path.join(base_dir, ".test_write")
        with open(test_file, 'w') as f:
            f.write('1')
        os.remove(test_file)
        db_path = DB_NAME
    except (IOError, OSError):
        # Fallback to user's AppData/home directory
        fallback_dir = os.path.join(os.path.expanduser("~"), "WorkTimeManager")
        if not os.path.exists(fallback_dir):
            os.makedirs(fallback_dir)
        db_path = os.path.join(fallback_dir, "worktime.db")
        
    return sqlite3.connect(db_path, timeout=10)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Work Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_logs (
            user_id INTEGER,
            date TEXT,
            type TEXT DEFAULT 'normal',
            clock_in TEXT,
            clock_out TEXT,
            non_work_time INTEGER DEFAULT 0,
            break_time INTEGER DEFAULT 0,
            work_time INTEGER DEFAULT 0,
            overtime_earned INTEGER DEFAULT 0,
            overtime_used INTEGER DEFAULT 0,
            description TEXT,
            PRIMARY KEY (user_id, date)
        )
    ''')
    
    # Overtime Vault Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS overtime_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            earned_minutes INTEGER DEFAULT 0,
            used_minutes INTEGER DEFAULT 0,
            expires_at TEXT,
            is_extended INTEGER DEFAULT 0
        )
    ''')
    
    # Admin Settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_settings (
            id INTEGER PRIMARY KEY,
            password TEXT
        )
    ''')
    
    # Insert default admin if not exists (password: 0000 for demo, user can change later)
    cursor.execute('SELECT COUNT(*) FROM admin_settings')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO admin_settings (id, password) VALUES (1, '0000')")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
