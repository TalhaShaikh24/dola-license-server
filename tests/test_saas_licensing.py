import os
import sys
import unittest
import datetime
from fastapi.testclient import TestClient

# Add workspace to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
server_dir = os.path.join(root_dir, "server")
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

import database
from licensing.hwid import get_hardware_id
from server import app

class TestSaaSLicensing(unittest.TestCase):
    admin_token = None
    user_id = None

    @classmethod
    def setUpClass(cls):
        # Use isolated temporary test database
        cls.test_db_path = os.path.join(server_dir, "test_saas.db")
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass
            
        database.DEFAULT_DB_PATH = cls.test_db_path
        database.init_db(cls.test_db_path)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass

    def test_01_hwid_generation(self):
        hwid1 = get_hardware_id()
        hwid2 = get_hardware_id()
        self.assertTrue(hwid1.startswith("DOLA-"))
        self.assertEqual(hwid1, hwid2, "HWID should be deterministic on the same device")
        print(f"\n[TEST] Generated Device HWID: {hwid1}")

    def test_02_super_admin_login(self):
        res = self.client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("token", data)
        TestSaaSLicensing.admin_token = data["token"]
        print("[TEST] Super Admin Login: Success")

    def test_03_user_registration_and_pending_check(self):
        hwid_device_a = "DOLA-AAAA-1111-2222-3333"
        reg_payload = {
            "email": "customer1@example.com",
            "password": "Password123!",
            "full_name": "Alice Customer",
            "hwid": hwid_device_a
        }
        res = self.client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("status"), "pending")
        TestSaaSLicensing.user_id = data.get("user_id")

        # Attempt to login while still pending
        login_res = self.client.post("/api/auth/login", json={
            "email": "customer1@example.com",
            "password": "Password123!",
            "hwid": hwid_device_a
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.json()
        self.assertFalse(login_data.get("success"))
        self.assertEqual(login_data.get("error"), "pending_approval")
        print("[TEST] Registration & Pending Approval Check: Success")

    def test_04_super_admin_approval_durations(self):
        headers = {"Authorization": f"Bearer {TestSaaSLicensing.admin_token}"}
        
        # Approve user with 1 Month duration
        approve_res = self.client.post(
            f"/api/admin/users/{TestSaaSLicensing.user_id}/approve",
            json={"plan_type": "1_month", "notes": "Monthly paid plan"},
            headers=headers
        )
        self.assertEqual(approve_res.status_code, 200)
        approve_data = approve_res.json()
        self.assertTrue(approve_data.get("success"))
        self.assertEqual(approve_data["user"]["status"], "active")
        self.assertEqual(approve_data["user"]["plan_type"], "1_month")
        self.assertIsNotNone(approve_data["user"]["expires_at"])
        print("[TEST] Super Admin Approval (1 Month): Success")

    def test_05_single_device_hwid_lock(self):
        hwid_device_a = "DOLA-AAAA-1111-2222-3333"
        hwid_device_b = "DOLA-BBBB-9999-8888-7777"

        # Login from Device A (Authorized PC)
        res_a = self.client.post("/api/auth/login", json={
            "email": "customer1@example.com",
            "password": "Password123!",
            "hwid": hwid_device_a
        })
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.json()
        self.assertTrue(data_a.get("success"))
        self.assertIn("token", data_a)
        user_token = data_a["token"]

        # Attempt to login with same account from Device B (Unauthorized PC)
        res_b = self.client.post("/api/auth/login", json={
            "email": "customer1@example.com",
            "password": "Password123!",
            "hwid": hwid_device_b
        })
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.json()
        self.assertFalse(data_b.get("success"))
        self.assertEqual(data_b.get("error"), "device_mismatch")
        print("[TEST] Single-Device Lock: Unauthorized Device B blocked successfully")

        # Verify session token for Device A
        verify_res = self.client.post("/api/auth/verify", json={
            "token": user_token,
            "hwid": hwid_device_a
        })
        self.assertEqual(verify_res.status_code, 200)
        self.assertTrue(verify_res.json().get("valid"))

    def test_06_admin_reset_hwid(self):
        headers = {"Authorization": f"Bearer {TestSaaSLicensing.admin_token}"}
        hwid_device_b = "DOLA-BBBB-9999-8888-7777"

        # Super Admin resets HWID binding
        reset_res = self.client.post(
            f"/api/admin/users/{TestSaaSLicensing.user_id}/reset-hwid",
            headers=headers
        )
        self.assertEqual(reset_res.status_code, 200)
        self.assertTrue(reset_res.json().get("success"))

        # Device B can now log in and bind
        res_b2 = self.client.post("/api/auth/login", json={
            "email": "customer1@example.com",
            "password": "Password123!",
            "hwid": hwid_device_b
        })
        self.assertEqual(res_b2.status_code, 200)
        data_b2 = res_b2.json()
        self.assertTrue(data_b2.get("success"))
        self.assertEqual(data_b2["user"]["hwid"], hwid_device_b)
        print("[TEST] Admin HWID Reset: Allowed PC migration successfully")

    def test_07_lifetime_license_approval(self):
        headers = {"Authorization": f"Bearer {TestSaaSLicensing.admin_token}"}
        approve_res = self.client.post(
            f"/api/admin/users/{TestSaaSLicensing.user_id}/approve",
            json={"plan_type": "lifetime", "notes": "VIP Lifetime Access"},
            headers=headers
        )
        self.assertEqual(approve_res.status_code, 200)
        approve_data = approve_res.json()
        self.assertEqual(approve_data["user"]["plan_type"], "lifetime")
        self.assertIsNone(approve_data["user"]["expires_at"])
        print("[TEST] Lifetime License Approval: Success")

if __name__ == "__main__":
    unittest.main()
