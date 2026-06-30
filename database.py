import sqlite3
import os
import sys
import hashlib
import hmac
import secrets
from datetime import datetime

PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 200_000
DEFAULT_ADMIN_PASSWORD = "gsiautomotive1234"

def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"

def verify_password(password, stored_password):
    if stored_password and stored_password.startswith(PASSWORD_HASH_PREFIX + "$"):
        try:
            _, iterations, salt_hex, digest_hex = stored_password.split("$", 3)
            expected = bytes.fromhex(digest_hex)
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                str(password).encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            )
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False

    return hmac.compare_digest(str(password or ""), str(stored_password or ""))

if getattr(sys, 'frozen', False):
    # If running as PyInstaller executable, put DB next to the .exe
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(__file__)

DB_NAME = os.path.join(base_dir, "worktime.db")

_resolved_db_path = None

def _resolve_db_path():
    global _resolved_db_path
    if _resolved_db_path is not None:
        return _resolved_db_path
        
    try:
        # Check if we can write to the base directory
        test_file = os.path.join(base_dir, ".test_write")
        with open(test_file, 'w') as f:
            f.write('1')
        os.remove(test_file)
        _resolved_db_path = DB_NAME
    except (IOError, OSError):
        # Fallback to user's AppData/home directory
        fallback_dir = os.path.join(os.path.expanduser("~"), "WorkTimeManager")
        if not os.path.exists(fallback_dir):
            os.makedirs(fallback_dir)
        _resolved_db_path = os.path.join(fallback_dir, "worktime.db")
    return _resolved_db_path

def get_connection():
    db_path = _resolve_db_path()
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
            user_id INTEGER,
            date TEXT,
            earned_minutes INTEGER DEFAULT 0,
            used_minutes INTEGER DEFAULT 0,
            expires_at TEXT,
            is_extended INTEGER DEFAULT 0
        )
    ''')
    
    # Check if user_id exists in overtime_vault (Migration)
    cursor.execute("PRAGMA table_info(overtime_vault)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'user_id' not in columns:
        cursor.execute("ALTER TABLE overtime_vault ADD COLUMN user_id INTEGER")
    
    # Admin Settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_settings (
            id INTEGER PRIMARY KEY,
            password TEXT
        )
    ''')
    
    # Insert default admin if not exists
    cursor.execute('SELECT COUNT(*) FROM admin_settings')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO admin_settings (id, password) VALUES (1, ?)", (hash_password(DEFAULT_ADMIN_PASSWORD),))
    else:
        # Migrate old plaintext defaults to a salted hash.
        cursor.execute(
            "UPDATE admin_settings SET password = ? WHERE id = 1 AND password IN ('0000', ?)",
            (hash_password(DEFAULT_ADMIN_PASSWORD), DEFAULT_ADMIN_PASSWORD),
        )
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
