import os
import datetime
import jwt
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, EmailStr

from database import (
    init_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    approve_user,
    reset_hwid,
    set_user_status,
    delete_user,
    update_login_and_hwid,
    verify_admin,
    verify_password
)

JWT_SECRET = os.getenv("SAAS_JWT_SECRET", "dola_super_secret_license_signing_key_2026_x99")
JWT_ALGORITHM = "HS256"

# Initialize FastAPI App
app = FastAPI(title="Dola AI SaaS License Server", version="1.0.0")

# Enable CORS for desktop app & web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup: initialize SQLite tables
@app.on_event("startup")
def on_startup():
    init_db()

# --- Pydantic Request Models ---
class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    hwid: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str
    hwid: str

class VerifyRequest(BaseModel):
    token: str
    hwid: str

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class ApproveRequest(BaseModel):
    plan_type: str  # '7_days', '1_month', '1_year', 'lifetime', 'custom'
    custom_date: Optional[str] = None
    notes: Optional[str] = None

class StatusUpdateRequest(BaseModel):
    status: str  # 'active', 'suspended', 'pending'

# --- Token Helpers ---
def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + (expires_delta or datetime.timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_admin(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privilege required")
    return payload

def check_user_expiry(user: dict) -> bool:
    """Returns True if expired."""
    expires_at_str = user.get("expires_at")
    if not expires_at_str:
        return False  # Lifetime or not set
    try:
        expires_at = datetime.datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        return now > expires_at
    except Exception:
        return False

# --- Public Client Endpoints ---

@app.post("/api/auth/register")
def register_user(req: RegisterRequest):
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not req.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")
        
    existing = get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")
        
    user = create_user(
        email=email,
        password_raw=req.password,
        full_name=req.full_name,
        hwid=req.hwid
    )
    return {
        "success": True,
        "message": "Registration submitted successfully! Your account is awaiting Super Admin approval.",
        "user_id": user["id"],
        "status": "pending"
    }

@app.post("/api/auth/login")
def login_user(req: LoginRequest):
    email = req.email.strip().lower()
    user = get_user_by_email(email)
    
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # Check Approval Status
    if user["status"] == "pending":
        return {
            "success": False,
            "error": "pending_approval",
            "message": "Your account is pending Super Admin approval. Please contact administrator."
        }
    if user["status"] == "suspended":
        return {
            "success": False,
            "error": "suspended",
            "message": "Your account has been suspended by the administrator."
        }
        
    # Check Expiry
    if check_user_expiry(user):
        set_user_status(user["id"], "expired")
        return {
            "success": False,
            "error": "expired",
            "message": "Your subscription has expired. Please contact administrator to renew."
        }

    # HWID Single-Device Lock Check
    current_hwid = req.hwid.strip() if req.hwid else ""
    bound_hwid = user.get("hwid")
    
    if bound_hwid and bound_hwid.strip():
        if bound_hwid.strip() != current_hwid:
            return {
                "success": False,
                "error": "device_mismatch",
                "message": f"Single-device restriction: This account is already bound to another PC ({bound_hwid}). Contact admin to transfer or reset your device.",
                "bound_hwid": bound_hwid
            }
    else:
        # Bind device on first login
        update_login_and_hwid(user["id"], current_hwid)
        user = get_user_by_id(user["id"])
        
    update_login_and_hwid(user["id"], current_hwid)
    
    # Generate Token
    token = create_access_token({
        "sub": str(user["id"]),
        "email": user["email"],
        "hwid": current_hwid,
        "role": "user"
    }, expires_delta=datetime.timedelta(days=14))
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "status": user["status"],
            "plan_type": user["plan_type"],
            "expires_at": user["expires_at"],
            "hwid": user["hwid"]
        }
    }

@app.post("/api/auth/verify")
def verify_session(req: VerifyRequest):
    try:
        payload = decode_token(req.token)
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
        
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
        
    if user["status"] != "active":
        return {
            "valid": False,
            "status": user["status"],
            "message": f"Account status is {user['status']}"
        }
        
    if check_user_expiry(user):
        set_user_status(user["id"], "expired")
        return {
            "valid": False,
            "status": "expired",
            "message": "Subscription expired"
        }
        
    # Check HWID
    req_hwid = req.hwid.strip() if req.hwid else ""
    if user.get("hwid") and user["hwid"].strip() != req_hwid:
        return {
            "valid": False,
            "status": "device_mismatch",
            "message": "Device mismatch. Single device lock violated."
        }
        
    return {
        "valid": True,
        "status": "active",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "status": user["status"],
            "plan_type": user["plan_type"],
            "expires_at": user["expires_at"],
            "hwid": user["hwid"]
        }
    }

# --- Super Admin Endpoints ---

@app.post("/api/admin/login")
def admin_login(req: AdminLoginRequest):
    if not verify_admin(req.username, req.password):
        raise HTTPException(status_code=401, detail="Invalid Super Admin credentials")
        
    token = create_access_token({
        "sub": req.username,
        "role": "admin"
    }, expires_delta=datetime.timedelta(days=2))
    
    return {
        "success": True,
        "token": token,
        "username": req.username
    }

@app.get("/api/admin/stats")
def get_admin_stats(admin=Depends(get_current_admin)):
    all_users = list_users()
    pending = sum(1 for u in all_users if u["status"] == "pending")
    active = sum(1 for u in all_users if u["status"] == "active")
    expired = sum(1 for u in all_users if u["status"] == "expired")
    suspended = sum(1 for u in all_users if u["status"] == "suspended")
    return {
        "total": len(all_users),
        "pending": pending,
        "active": active,
        "expired": expired,
        "suspended": suspended
    }

@app.get("/api/admin/users")
def get_admin_users(search: Optional[str] = None, status: Optional[str] = None, admin=Depends(get_current_admin)):
    users = list_users(search=search, status_filter=status)
    # Sanitize password hash before returning
    for u in users:
        u.pop("password_hash", None)
    return {"users": users}

@app.post("/api/admin/users/{user_id}/approve")
def admin_approve_user(user_id: int, req: ApproveRequest, admin=Depends(get_current_admin)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    updated = approve_user(
        user_id=user_id,
        plan_type=req.plan_type,
        custom_date=req.custom_date,
        notes=req.notes
    )
    updated.pop("password_hash", None)
    return {"success": True, "message": f"User approved with {req.plan_type} plan", "user": updated}

@app.post("/api/admin/users/{user_id}/reset-hwid")
def admin_reset_hwid(user_id: int, admin=Depends(get_current_admin)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    updated = reset_hwid(user_id)
    updated.pop("password_hash", None)
    return {"success": True, "message": "Device binding (HWID) reset successfully", "user": updated}

@app.post("/api/admin/users/{user_id}/status")
def admin_set_status(user_id: int, req: StatusUpdateRequest, admin=Depends(get_current_admin)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    updated = set_user_status(user_id, req.status)
    updated.pop("password_hash", None)
    return {"success": True, "message": f"Status updated to {req.status}", "user": updated}

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin=Depends(get_current_admin)):
    success = delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "message": "User deleted"}

# --- Admin Dashboard Static Files ---
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/admin")
@app.get("/admin/")
def admin_dashboard():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/")
def root_redirect():
    return RedirectResponse(url="/admin")
