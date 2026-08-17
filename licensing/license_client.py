import json
import os
import requests
from typing import Optional, Dict, Any, Tuple
from licensing.hwid import get_hardware_id

DEFAULT_SERVER_URL = os.getenv(
    "DOLA_LICENSE_SERVER_URL",
    "https://dola-license-server-gullubut2-gmailcoms-projects.vercel.app"
)
SESSION_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".license_session.json")
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "license_config.json")

class LicenseClient:
    def __init__(self, server_url: Optional[str] = None):
        self.server_url = (server_url or self._load_server_url() or DEFAULT_SERVER_URL).rstrip("/")
        self.hwid = get_hardware_id()
        self.session_token: Optional[str] = None
        self.user_data: Optional[Dict[str, Any]] = None
        self._load_cached_session()

    def _load_server_url(self) -> Optional[str]:
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("server_url")
            except Exception:
                pass
        return None

    def save_server_url(self, new_url: str):
        self.server_url = new_url.strip().rstrip("/")
        try:
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump({"server_url": self.server_url}, f, indent=2)
        except Exception as e:
            print(f"Error saving server url: {e}")

    def _load_cached_session(self):
        if os.path.exists(SESSION_FILE_PATH):
            try:
                with open(SESSION_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.session_token = data.get("token")
                    self.user_data = data.get("user")
            except Exception:
                self.session_token = None
                self.user_data = None

    def _save_session(self, token: str, user: dict):
        self.session_token = token
        self.user_data = user
        try:
            with open(SESSION_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump({"token": token, "user": user}, f, indent=2)
        except Exception as e:
            print(f"Error caching session: {e}")

    def clear_session(self):
        self.session_token = None
        self.user_data = None
        if os.path.exists(SESSION_FILE_PATH):
            try:
                os.remove(SESSION_FILE_PATH)
            except Exception:
                pass

    def register(self, email: str, password: str, full_name: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Register a new user account.
        Returns: (success: bool, message: str, raw_response: dict)
        """
        url = f"{self.server_url}/api/auth/register"
        payload = {
            "email": email.strip(),
            "password": password,
            "full_name": full_name.strip(),
            "hwid": self.hwid
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            try:
                data = res.json()
            except Exception:
                return False, f"Server error ({res.status_code}). Please try again.", {}
            if res.status_code == 200 and data.get("success"):
                return True, data.get("message", "Registration submitted"), data
            else:
                return False, data.get("detail", data.get("message", "Registration failed")), data
        except requests.exceptions.ConnectionError:
            return False, "Could not connect to license server. Please ensure internet is connected.", {}
        except Exception as e:
            return False, f"Registration error: {str(e)}", {}

    def login(self, email: str, password: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Login user and verify HWID binding & license validity.
        Returns: (success: bool, message: str, raw_response: dict)
        """
        url = f"{self.server_url}/api/auth/login"
        payload = {
            "email": email.strip(),
            "password": password,
            "hwid": self.hwid
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            try:
                data = res.json()
            except Exception:
                return False, f"Server error ({res.status_code}). Please try again.", {}
            
            if res.status_code == 200 and data.get("success"):
                token = data.get("token")
                user = data.get("user")
                self._save_session(token, user)
                return True, "Login successful", data
            else:
                msg = data.get("message", data.get("detail", "Login failed"))
                return False, msg, data
        except requests.exceptions.ConnectionError:
            return False, "Could not reach license server. Check internet connection.", {}
        except Exception as e:
            return False, f"Login error: {str(e)}", {}

    def verify_current_session(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verify cached session token and check online license status and HWID.
        Returns: (is_valid: bool, status_message: str, user_dict: dict)
        """
        if not self.session_token:
            return False, "No active session", None

        url = f"{self.server_url}/api/auth/verify"
        payload = {
            "token": self.session_token,
            "hwid": self.hwid
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            data = res.json()
            
            if res.status_code == 200 and data.get("valid"):
                self.user_data = data.get("user")
                return True, "License valid and active", self.user_data
            else:
                status_code = data.get("status", "invalid")
                msg = data.get("message", data.get("detail", "License invalid or expired"))
                if status_code in ["pending", "expired", "suspended", "device_mismatch"]:
                    # Keep user info if available for UI display
                    return False, msg, data.get("user") or self.user_data
                self.clear_session()
                return False, msg, None
        except requests.exceptions.ConnectionError:
            # Network issue: If we have valid cached user data, allow graceful check or notice
            if self.user_data:
                return False, "Network offline: Unable to verify license server online.", self.user_data
            return False, "Unable to reach license server.", None
        except Exception as e:
            return False, f"Verification failed: {str(e)}", None

    def verify_email(self, email: str, otp: str) -> Tuple[bool, str]:
        url = f"{self.server_url}/api/auth/verify-email"
        try:
            res = requests.post(url, json={"email": email.strip(), "otp": otp.strip()}, timeout=10)
            data = res.json()
            return data.get("success", False), data.get("message", "Verification failed")
        except Exception as e:
            return False, f"Verification error: {str(e)}"

    def resend_otp(self, email: str) -> Tuple[bool, str]:
        url = f"{self.server_url}/api/auth/resend-otp"
        try:
            res = requests.post(url, json={"email": email.strip()}, timeout=10)
            data = res.json()
            return data.get("success", False), data.get("message", "Failed to resend code")
        except Exception as e:
            return False, f"Network error: {str(e)}"

    def forgot_password(self, email: str) -> Tuple[bool, str]:
        url = f"{self.server_url}/api/auth/forgot-password"
        try:
            res = requests.post(url, json={"email": email.strip()}, timeout=10)
            data = res.json()
            return data.get("success", False), data.get("message", "Failed to send reset code")
        except Exception as e:
            return False, f"Network error: {str(e)}"

    def reset_password(self, email: str, otp: str, new_password: str) -> Tuple[bool, str]:
        url = f"{self.server_url}/api/auth/reset-password"
        try:
            res = requests.post(url, json={"email": email.strip(), "otp": otp.strip(), "new_password": new_password}, timeout=10)
            data = res.json()
            return data.get("success", False), data.get("message", "Password reset failed")
        except Exception as e:
            return False, f"Network error: {str(e)}"

    def log_usage_async(self, op_type: str, count: int = 1, details: str = ""):
        """Asynchronously log video processing operations to SaaS analytics without blocking."""
        if not self.session_token:
            return
            
        import threading
        def _send():
            try:
                url = f"{self.server_url}/api/analytics/log-event"
                payload = {
                    "token": self.session_token,
                    "op_type": op_type,
                    "count": count,
                    "details": str(details)[:200]
                }
                requests.post(url, json=payload, timeout=8)
            except Exception:
                pass
                
        t = threading.Thread(target=_send, daemon=True)
        t.start()

    def get_plan_display(self) -> str:
        if not self.user_data:
            return "No Active License"
        plan = self.user_data.get("plan_type", "none")
        if plan == "lifetime":
            return "👑 Lifetime License"
        elif plan == "7_days":
            return "7 Days Trial"
        elif plan == "1_month":
            return "Monthly License"
        elif plan == "1_year":
            return "Annual License"
        return f"{plan.capitalize()} License"

# Global client singleton
license_client = LicenseClient()
