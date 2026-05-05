import sqlite3
import os
import sys
from datetime import datetime

if getattr(sys, 'frozen', False):
    # If running as PyInstaller executable, put DB next to the .exe
    DB_NAME = os.path.join(os.path.dirname(sys.executable), "worktime.db")
else:
    DB_NAME = "worktime.db"

def get_connection():
    return sqlite3.connect(DB_NAME, timeout=10)

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
