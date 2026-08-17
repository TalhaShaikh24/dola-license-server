import sqlite3
import os
import datetime
import bcrypt
from typing import Optional, List, Dict, Any

DEFAULT_DB_PATH = os.getenv("DATABASE_PATH")
if not DEFAULT_DB_PATH:
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        DEFAULT_DB_PATH = "/tmp/saas_licenses.db"
    else:
        DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saas_licenses.db")

_db_initialized = False

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    global _db_initialized
    target_path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    if not _db_initialized and target_path == DEFAULT_DB_PATH:
        _db_initialized = True
        try:
            init_db(target_path)
        except Exception:
            pass
    return conn

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def init_db(db_path: Optional[str] = None):
    """Initialize database tables and create default super admin if not exists."""
    target_path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    with get_connection(target_path) as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                plan_type TEXT DEFAULT 'none',
                expires_at TEXT,
                hwid TEXT,
                hwid_registered_at TEXT,
                created_at TEXT NOT NULL,
                approved_at TEXT,
                last_login_at TEXT,
                notes TEXT,
                is_email_verified INTEGER DEFAULT 0,
                verification_code TEXT,
                verification_code_expires_at TEXT,
                reset_code TEXT,
                reset_code_expires_at TEXT
            )
        """)

        # Migration helper for existing DBs
        for col_def in [
            ("is_email_verified", "INTEGER DEFAULT 0"),
            ("verification_code", "TEXT"),
            ("verification_code_expires_at", "TEXT"),
            ("reset_code", "TEXT"),
            ("reset_code_expires_at", "TEXT"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_def[0]} {col_def[1]}")
            except Exception:
                pass
        
        # Admin table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Check if default admin exists
        cursor.execute("SELECT id FROM admins WHERE username = 'admin'")
        if not cursor.fetchone():
            default_hash = hash_password("admin123")
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                ("admin", default_hash, now_iso)
            )
        conn.commit()

def calculate_expiry(plan_type: str, custom_date: Optional[str] = None) -> Optional[str]:
    """Calculate expiration ISO timestamp based on plan duration."""
    now = datetime.datetime.now(datetime.timezone.utc)
    if plan_type == "7_days":
        expiry = now + datetime.timedelta(days=7)
        return expiry.isoformat()
    elif plan_type == "1_month":
        expiry = now + datetime.timedelta(days=30)
        return expiry.isoformat()
    elif plan_type == "1_year":
        expiry = now + datetime.timedelta(days=365)
        return expiry.isoformat()
    elif plan_type == "lifetime":
        return None
    elif plan_type == "custom" and custom_date:
        return custom_date
    return None

def create_user(email: str, password_raw: str, full_name: str, hwid: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pwd_hash = hash_password(password_raw)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (email, password_hash, full_name, status, created_at, hwid)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (email.strip().lower(), pwd_hash, full_name.strip(), now_iso, hwid)
        )
        user_id = cursor.lastrowid
        conn.commit()
    return get_user_by_id(user_id, db_path)

def get_user_by_email(email: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def list_users(search: Optional[str] = None, status_filter: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM users WHERE 1=1"
        params = []
        
        if status_filter and status_filter != "all":
            query += " AND status = ?"
            params.append(status_filter)
            
        if search:
            query += " AND (email LIKE ? OR full_name LIKE ? OR hwid LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])
            
        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def approve_user(user_id: int, plan_type: str, custom_date: Optional[str] = None, notes: Optional[str] = None, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    expiry_iso = calculate_expiry(plan_type, custom_date)
    
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users 
            SET status = 'active', plan_type = ?, expires_at = ?, approved_at = ?, notes = COALESCE(?, notes)
            WHERE id = ?
            """,
            (plan_type, expiry_iso, now_iso, notes, user_id)
        )
        conn.commit()
    return get_user_by_id(user_id, db_path)

def reset_hwid(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET hwid = NULL, hwid_registered_at = NULL WHERE id = ?",
            (user_id,)
        )
        conn.commit()
    return get_user_by_id(user_id, db_path)

def set_user_status(user_id: int, status: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
        conn.commit()
    return get_user_by_id(user_id, db_path)

def delete_user(user_id: int, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def update_login_and_hwid(user_id: int, hwid: str, db_path: Optional[str] = None):
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # If user has no HWID bound yet, bind it now
        cursor.execute(
            """
            UPDATE users
            SET last_login_at = ?,
                hwid = CASE WHEN hwid IS NULL OR hwid = '' THEN ? ELSE hwid END,
                hwid_registered_at = CASE WHEN hwid IS NULL OR hwid = '' THEN ? ELSE hwid_registered_at END
            WHERE id = ?
            """,
            (now_iso, hwid, now_iso, user_id)
        )
        conn.commit()

def verify_admin(username: str, password_raw: str, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM admins WHERE username = ?", (username.strip(),))
        row = cursor.fetchone()
        if row and verify_password(password_raw, row["password_hash"]):
            return True
    return False

def update_admin_password(username: str, new_password_raw: str, db_path: Optional[str] = None):
    new_hash = hash_password(new_password_raw)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE admins SET password_hash = ? WHERE username = ?", (new_hash, username.strip()))
        conn.commit()

def set_user_verification_otp(user_id: int, otp_code: str, db_path: Optional[str] = None):
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = (now + datetime.timedelta(minutes=15)).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET verification_code = ?, verification_code_expires_at = ? WHERE id = ?",
            (otp_code, expires, user_id)
        )
        conn.commit()

def verify_user_email_otp(email: str, otp_code: str, db_path: Optional[str] = None) -> tuple[bool, str]:
    user = get_user_by_email(email, db_path)
    if not user:
        return False, "User not found"
    if user.get("is_email_verified") == 1:
        return True, "Email is already verified"
    
    code = user.get("verification_code")
    expires_str = user.get("verification_code_expires_at")
    
    if not code or code.strip() != otp_code.strip():
        return False, "Invalid verification code"
        
    if expires_str:
        try:
            expires_dt = datetime.datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if datetime.datetime.now(datetime.timezone.utc) > expires_dt:
                return False, "Verification code has expired. Please request a new code."
        except Exception:
            pass
            
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_email_verified = 1, verification_code = NULL, verification_code_expires_at = NULL WHERE id = ?",
            (user["id"],)
        )
        conn.commit()
    return True, "Email verified successfully!"

def set_password_reset_otp(email: str, otp_code: str, db_path: Optional[str] = None) -> bool:
    user = get_user_by_email(email, db_path)
    if not user:
        return False
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = (now + datetime.timedelta(minutes=15)).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET reset_code = ?, reset_code_expires_at = ? WHERE id = ?",
            (otp_code, expires, user["id"])
        )
        conn.commit()
    return True

def reset_password_with_otp(email: str, otp_code: str, new_password_raw: str, db_path: Optional[str] = None) -> tuple[bool, str]:
    user = get_user_by_email(email, db_path)
    if not user:
        return False, "User not found"
    
    code = user.get("reset_code")
    expires_str = user.get("reset_code_expires_at")
    
    if not code or code.strip() != otp_code.strip():
        return False, "Invalid reset code"
        
    if expires_str:
        try:
            expires_dt = datetime.datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if datetime.datetime.now(datetime.timezone.utc) > expires_dt:
                return False, "Reset code has expired. Please request a new code."
        except Exception:
            pass
            
    new_hash = hash_password(new_password_raw)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ?, reset_code = NULL, reset_code_expires_at = NULL WHERE id = ?",
            (new_hash, user["id"])
        )
        conn.commit()
    return True, "Password reset successfully! You can now sign in with your new password."
