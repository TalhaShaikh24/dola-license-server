import sqlite3
import os
import datetime
import bcrypt
import requests
from typing import Optional, List, Dict, Any

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()

DEFAULT_DB_PATH = os.getenv("DATABASE_PATH")
if not DEFAULT_DB_PATH:
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        DEFAULT_DB_PATH = "/tmp/saas_licenses.db"
    else:
        DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saas_licenses.db")

_db_initialized = False

def is_turso_enabled() -> bool:
    return bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)

# --- Turso Cloud HTTP Engine ---
def _turso_request(statements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Execute SQL statements against Turso Serverless SQLite via HTTP Pipeline API."""
    url = TURSO_DATABASE_URL.replace("libsql://", "https://").rstrip("/") + "/v2/pipeline"
    requests_payload = []
    for stmt in statements:
        sql = stmt.get("sql", "")
        params = stmt.get("params", [])
        args = []
        for p in params:
            if p is None:
                args.append({"type": "null"})
            elif isinstance(p, bool):
                args.append({"type": "integer", "value": "1" if p else "0"})
            elif isinstance(p, int):
                args.append({"type": "integer", "value": str(p)})
            elif isinstance(p, float):
                args.append({"type": "float", "value": p})
            else:
                args.append({"type": "text", "value": str(p)})
        requests_payload.append({
            "type": "execute",
            "stmt": {"sql": sql, "args": args}
        })
    requests_payload.append({"type": "close"})

    headers = {
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    r = requests.post(url, json={"requests": requests_payload}, headers=headers, timeout=12)
    if r.status_code != 200:
        raise Exception(f"Turso Error {r.status_code}: {r.text}")
    
    data = r.json()
    results = []
    for res in data.get("results", []):
        if res.get("type") == "error":
            raise Exception(f"Turso Query Error: {res.get('error', {}).get('message', 'Unknown error')}")
        resp_obj = res.get("response", {}).get("result", {})
        cols = [c.get("name") for c in resp_obj.get("cols", [])]
        rows = []
        for row in resp_obj.get("rows", []):
            row_dict = {}
            for i, col_name in enumerate(cols):
                val_obj = row[i] if i < len(row) else None
                val = val_obj.get("value") if isinstance(val_obj, dict) else val_obj
                if isinstance(val_obj, dict) and val_obj.get("type") == "integer" and val is not None:
                    try:
                        val = int(val)
                    except Exception:
                        pass
                row_dict[col_name] = val
            rows.append(row_dict)
        results.append({
            "rows": rows,
            "rows_affected": resp_obj.get("rows_affected", 0),
            "last_insert_rowid": resp_obj.get("last_insert_rowid")
        })
    return results

def _turso_query(sql: str, params: list = None) -> List[Dict[str, Any]]:
    results = _turso_request([{"sql": sql, "params": params or []}])
    return results[0]["rows"] if results else []

def _turso_execute(sql: str, params: list = None) -> Dict[str, Any]:
    results = _turso_request([{"sql": sql, "params": params or []}])
    return results[0] if results else {"rows_affected": 0, "last_insert_rowid": None}


# --- Local SQLite Engine Fallback ---
def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if not hashed_password:
            return False
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def init_db(db_path: Optional[str] = None):
    """Initialize database tables and create default super admin if not exists."""
    global _db_initialized
    _db_initialized = True

    if is_turso_enabled():
        # Initialize Turso Cloud Tables
        schema_queries = [
            """
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
                reset_code_expires_at TEXT,
                watermark_count INTEGER DEFAULT 0,
                combine_count INTEGER DEFAULT 0,
                total_ops_count INTEGER DEFAULT 0,
                last_activity_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT,
                op_type TEXT NOT NULL,
                item_count INTEGER DEFAULT 1,
                details TEXT,
                created_at TEXT NOT NULL
            )
            """
        ]
        for q in schema_queries:
            _turso_execute(q)

        # Check default admin
        admin_rows = _turso_query("SELECT id FROM admins WHERE username = 'admin'")
        if not admin_rows:
            default_hash = hash_password("admin123")
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            _turso_execute(
                "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                ["admin", default_hash, now_iso]
            )
        return

    # Local SQLite
    target_path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    with get_connection(target_path) as conn:
        cursor = conn.cursor()
        
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
                reset_code_expires_at TEXT,
                watermark_count INTEGER DEFAULT 0,
                combine_count INTEGER DEFAULT 0,
                total_ops_count INTEGER DEFAULT 0,
                last_activity_at TEXT
            )
        """)

        # Migration helper for existing local DBs
        for col_def in [
            ("is_email_verified", "INTEGER DEFAULT 0"),
            ("verification_code", "TEXT"),
            ("verification_code_expires_at", "TEXT"),
            ("reset_code", "TEXT"),
            ("reset_code_expires_at", "TEXT"),
            ("watermark_count", "INTEGER DEFAULT 0"),
            ("combine_count", "INTEGER DEFAULT 0"),
            ("total_ops_count", "INTEGER DEFAULT 0"),
            ("last_activity_at", "TEXT"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_def[0]} {col_def[1]}")
            except Exception:
                pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT,
                op_type TEXT NOT NULL,
                item_count INTEGER DEFAULT 1,
                details TEXT,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
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
    now = datetime.datetime.now(datetime.timezone.utc)
    if plan_type == "7_days":
        return (now + datetime.timedelta(days=7)).isoformat()
    elif plan_type == "1_month":
        return (now + datetime.timedelta(days=30)).isoformat()
    elif plan_type == "1_year":
        return (now + datetime.timedelta(days=365)).isoformat()
    elif plan_type == "lifetime":
        return None
    elif plan_type == "custom" and custom_date:
        return custom_date
    return None

def create_user(email: str, password_raw: str, full_name: str, hwid: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pwd_hash = hash_password(password_raw)
    clean_email = email.strip().lower()

    if is_turso_enabled():
        res = _turso_execute(
            """
            INSERT INTO users (email, password_hash, full_name, status, created_at, hwid)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            [clean_email, pwd_hash, full_name.strip(), now_iso, hwid]
        )
        return get_user_by_email(clean_email)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (email, password_hash, full_name, status, created_at, hwid)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (clean_email, pwd_hash, full_name.strip(), now_iso, hwid)
        )
        user_id = cursor.lastrowid
        conn.commit()
    return get_user_by_id(user_id, db_path)

def get_user_by_email(email: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    clean_email = email.strip().lower()
    if is_turso_enabled():
        rows = _turso_query("SELECT * FROM users WHERE email = ?", [clean_email])
        return rows[0] if rows else None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (clean_email,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if is_turso_enabled():
        rows = _turso_query("SELECT * FROM users WHERE id = ?", [user_id])
        return rows[0] if rows else None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def list_users(search: Optional[str] = None, status_filter: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
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

    if is_turso_enabled():
        return _turso_query(query, params)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

def approve_user(user_id: int, plan_type: str, custom_date: Optional[str] = None, notes: Optional[str] = None, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    expiry_iso = calculate_expiry(plan_type, custom_date)
    
    if is_turso_enabled():
        _turso_execute(
            """
            UPDATE users 
            SET status = 'active',
                plan_type = ?,
                expires_at = ?,
                approved_at = ?,
                notes = CASE WHEN ? IS NOT NULL THEN ? ELSE notes END
            WHERE id = ?
            """,
            [plan_type, expiry_iso, now_iso, notes, notes, user_id]
        )
        return get_user_by_id(user_id)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users 
            SET status = 'active',
                plan_type = ?,
                expires_at = ?,
                approved_at = ?,
                notes = CASE WHEN ? IS NOT NULL THEN ? ELSE notes END
            WHERE id = ?
            """,
            (plan_type, expiry_iso, now_iso, notes, notes, user_id)
        )
        conn.commit()
    return get_user_by_id(user_id, db_path)

def reset_hwid(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if is_turso_enabled():
        _turso_execute("UPDATE users SET hwid = NULL, hwid_registered_at = NULL WHERE id = ?", [user_id])
        return get_user_by_id(user_id)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET hwid = NULL, hwid_registered_at = NULL WHERE id = ?", (user_id,))
        conn.commit()
    return get_user_by_id(user_id, db_path)

def set_user_status(user_id: int, status: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if is_turso_enabled():
        _turso_execute("UPDATE users SET status = ? WHERE id = ?", [status, user_id])
        return get_user_by_id(user_id)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
        conn.commit()
    return get_user_by_id(user_id, db_path)

def delete_user(user_id: int, db_path: Optional[str] = None) -> bool:
    if is_turso_enabled():
        res = _turso_execute("DELETE FROM users WHERE id = ?", [user_id])
        return res.get("rows_affected", 0) > 0

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def update_login_and_hwid(user_id: int, hwid: str, db_path: Optional[str] = None):
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if is_turso_enabled():
        _turso_execute(
            """
            UPDATE users
            SET last_login_at = ?,
                hwid = CASE WHEN hwid IS NULL OR hwid = '' THEN ? ELSE hwid END,
                hwid_registered_at = CASE WHEN hwid IS NULL OR hwid = '' THEN ? ELSE hwid_registered_at END
            WHERE id = ?
            """,
            [now_iso, hwid, now_iso, user_id]
        )
        return

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
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
    clean_user = username.strip()
    if is_turso_enabled():
        rows = _turso_query("SELECT password_hash FROM admins WHERE username = ?", [clean_user])
        if rows and verify_password(password_raw, rows[0].get("password_hash")):
            return True
        return False

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM admins WHERE username = ?", (clean_user,))
        row = cursor.fetchone()
        if row and verify_password(password_raw, row["password_hash"]):
            return True
    return False

def update_admin_password(username: str, new_password_raw: str, db_path: Optional[str] = None):
    new_hash = hash_password(new_password_raw)
    clean_user = username.strip()
    if is_turso_enabled():
        _turso_execute("UPDATE admins SET password_hash = ? WHERE username = ?", [new_hash, clean_user])
        return

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE admins SET password_hash = ? WHERE username = ?", (new_hash, clean_user))
        conn.commit()

def set_user_verification_otp(user_id: int, otp_code: str, db_path: Optional[str] = None):
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = (now + datetime.timedelta(minutes=15)).isoformat()
    if is_turso_enabled():
        _turso_execute("UPDATE users SET verification_code = ?, verification_code_expires_at = ? WHERE id = ?", [otp_code, expires, user_id])
        return

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
    
    if not code or str(code).strip() != str(otp_code).strip():
        return False, "Invalid verification code"
        
    if expires_str:
        try:
            expires_dt = datetime.datetime.fromisoformat(str(expires_str).replace("Z", "+00:00"))
            if datetime.datetime.now(datetime.timezone.utc) > expires_dt:
                return False, "Verification code has expired. Please request a new code."
        except Exception:
            pass
            
    if is_turso_enabled():
        _turso_execute(
            "UPDATE users SET is_email_verified = 1, verification_code = NULL, verification_code_expires_at = NULL WHERE id = ?",
            [user["id"]]
        )
        return True, "Email verified successfully!"

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
    if is_turso_enabled():
        _turso_execute("UPDATE users SET reset_code = ?, reset_code_expires_at = ? WHERE id = ?", [otp_code, expires, user["id"]])
        return True

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
    
    if not code or str(code).strip() != str(otp_code).strip():
        return False, "Invalid reset code"
        
    if expires_str:
        try:
            expires_dt = datetime.datetime.fromisoformat(str(expires_str).replace("Z", "+00:00"))
            if datetime.datetime.now(datetime.timezone.utc) > expires_dt:
                return False, "Reset code has expired. Please request a new code."
        except Exception:
            pass
            
    new_hash = hash_password(new_password_raw)
    if is_turso_enabled():
        _turso_execute(
            "UPDATE users SET password_hash = ?, reset_code = NULL, reset_code_expires_at = NULL WHERE id = ?",
            [new_hash, user["id"]]
        )
        return True, "Password reset successfully! You can now sign in with your new password."

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ?, reset_code = NULL, reset_code_expires_at = NULL WHERE id = ?",
            (new_hash, user["id"])
        )
        conn.commit()
    return True, "Password reset successfully! You can now sign in with your new password."

def record_usage_event(user_id: int, op_type: str, item_count: int = 1, details: Optional[str] = None, db_path: Optional[str] = None) -> bool:
    user = get_user_by_id(user_id, db_path)
    if not user:
        return False
    
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    email = user.get("email", "")
    
    is_watermark = "watermark" in op_type
    is_combine = "combine" in op_type
    
    wm_increment = item_count if is_watermark else 0
    combine_increment = item_count if is_combine else 0
    total_increment = item_count
    
    if is_turso_enabled():
        _turso_execute(
            """
            UPDATE users 
            SET watermark_count = COALESCE(watermark_count, 0) + ?,
                combine_count = COALESCE(combine_count, 0) + ?,
                total_ops_count = COALESCE(total_ops_count, 0) + ?,
                last_activity_at = ?
            WHERE id = ?
            """,
            [wm_increment, combine_increment, total_increment, now_iso, user_id]
        )
        _turso_execute(
            """
            INSERT INTO activity_logs (user_id, email, op_type, item_count, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [user_id, email, op_type, item_count, details or "", now_iso]
        )
        return True

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users 
            SET watermark_count = COALESCE(watermark_count, 0) + ?,
                combine_count = COALESCE(combine_count, 0) + ?,
                total_ops_count = COALESCE(total_ops_count, 0) + ?,
                last_activity_at = ?
            WHERE id = ?
            """,
            (wm_increment, combine_increment, total_increment, now_iso, user_id)
        )
        cursor.execute(
            """
            INSERT INTO activity_logs (user_id, email, op_type, item_count, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, email, op_type, item_count, details or "", now_iso)
        )
        conn.commit()
    return True

def get_admin_analytics_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
    yesterday_iso = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)).isoformat()

    if is_turso_enabled():
        agg_rows = _turso_query("""
            SELECT 
                COUNT(*) as total_users,
                COALESCE(SUM(watermark_count), 0) as total_watermarks_removed,
                COALESCE(SUM(combine_count), 0) as total_videos_combined,
                COALESCE(SUM(total_ops_count), 0) as total_operations
            FROM users
        """)
        agg = agg_rows[0] if agg_rows else {}
        top_users = _turso_query("""
            SELECT id, email, full_name, plan_type, status, watermark_count, combine_count, total_ops_count, last_activity_at
            FROM users
            WHERE COALESCE(total_ops_count, 0) > 0
            ORDER BY total_ops_count DESC
            LIMIT 10
        """)
        recent_activities = _turso_query("""
            SELECT id, user_id, email, op_type, item_count, details, created_at
            FROM activity_logs
            ORDER BY id DESC
            LIMIT 25
        """)
        today_rows = _turso_query("""
            SELECT 
                COALESCE(SUM(CASE WHEN op_type LIKE '%watermark%' THEN item_count ELSE 0 END), 0) as today_watermarks,
                COALESCE(SUM(CASE WHEN op_type LIKE '%combine%' THEN item_count ELSE 0 END), 0) as today_combines,
                COUNT(DISTINCT user_id) as active_users_24h
            FROM activity_logs
            WHERE created_at >= ?
        """, [yesterday_iso])
        today_stats = today_rows[0] if today_rows else {}

        return {
            "total_watermarks_removed": agg.get("total_watermarks_removed", 0),
            "total_videos_combined": agg.get("total_videos_combined", 0),
            "total_operations": agg.get("total_operations", 0),
            "today_watermarks": today_stats.get("today_watermarks", 0),
            "today_combines": today_stats.get("today_combines", 0),
            "active_users_today": today_stats.get("active_users_24h", 0),
            "top_users": top_users,
            "recent_activities": recent_activities
        }

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_users,
                COALESCE(SUM(watermark_count), 0) as total_watermarks_removed,
                COALESCE(SUM(combine_count), 0) as total_videos_combined,
                COALESCE(SUM(total_ops_count), 0) as total_operations
            FROM users
        """)
        agg = dict(cursor.fetchone() or {})
        cursor.execute("""
            SELECT id, email, full_name, plan_type, status, watermark_count, combine_count, total_ops_count, last_activity_at
            FROM users
            WHERE COALESCE(total_ops_count, 0) > 0
            ORDER BY total_ops_count DESC
            LIMIT 10
        """)
        top_users = [dict(r) for r in cursor.fetchall()]
        cursor.execute("""
            SELECT id, user_id, email, op_type, item_count, details, created_at
            FROM activity_logs
            ORDER BY id DESC
            LIMIT 25
        """)
        recent_activities = [dict(r) for r in cursor.fetchall()]
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN op_type LIKE '%watermark%' THEN item_count ELSE 0 END), 0) as today_watermarks,
                COALESCE(SUM(CASE WHEN op_type LIKE '%combine%' THEN item_count ELSE 0 END), 0) as today_combines,
                COUNT(DISTINCT user_id) as active_users_24h
            FROM activity_logs
            WHERE created_at >= ?
        """, (yesterday_iso,))
        today_stats = dict(cursor.fetchone() or {})
        
        return {
            "total_watermarks_removed": agg.get("total_watermarks_removed", 0),
            "total_videos_combined": agg.get("total_videos_combined", 0),
            "total_operations": agg.get("total_operations", 0),
            "today_watermarks": today_stats.get("today_watermarks", 0),
            "today_combines": today_stats.get("today_combines", 0),
            "active_users_today": today_stats.get("active_users_24h", 0),
            "top_users": top_users,
            "recent_activities": recent_activities
        }
