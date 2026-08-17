import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QWidget, QFrame, QMessageBox, QApplication, QSpacerItem,
    QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QIcon, QCursor, QClipboard

from licensing.license_client import license_client

AUTH_DIALOG_STYLE = """
QDialog {
    background-color: #0b0f19;
    color: #f3f4f6;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.08);
    background-color: #111827;
    border-radius: 12px;
    top: -1px;
}

QTabBar::tab {
    background: #0b0f19;
    color: #9ca3af;
    padding: 10px 22px;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background: #111827;
    color: #6366f1;
    border-color: rgba(255, 255, 255, 0.08);
    border-bottom: 1px solid #111827;
}

QTabBar::tab:hover:!selected {
    background: #1e293b;
    color: #e5e7eb;
}

QLineEdit {
    background-color: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 10px 14px;
    color: #ffffff;
    font-size: 13px;
    selection-background-color: #6366f1;
}

QLineEdit:focus {
    border: 1px solid #6366f1;
    background-color: rgba(15, 23, 42, 0.95);
}

QPushButton.primary-btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #4f46e5);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 700;
}

QPushButton.primary-btn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #4338ca);
}

QPushButton.primary-btn:pressed {
    background-color: #3730a3;
}

QPushButton.primary-btn:disabled {
    background: #374151;
    color: #9ca3af;
}

QPushButton.outline-btn {
    background-color: transparent;
    color: #9ca3af;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton.outline-btn:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.3);
}

QLabel {
    color: #d1d5db;
    font-size: 13px;
}

QLabel.title-label {
    font-size: 18px;
    font-weight: 800;
    color: #ffffff;
}

QLabel.sub-label {
    font-size: 12px;
    color: #9ca3af;
}

QLabel.banner-error {
    background-color: rgba(244, 63, 94, 0.15);
    border: 1px solid rgba(244, 63, 94, 0.35);
    color: #fb7185;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 12px;
}

QLabel.banner-warning {
    background-color: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #fbbf24;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 12px;
}

QLabel.banner-success {
    background-color: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34d399;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 12px;
}
"""

class AuthWorker(QThread):
    finished = pyqtSignal(bool, str, dict)

    def __init__(self, action: str, **kwargs):
        super().__init__()
        self.action = action
        self.kwargs = kwargs

    def run(self):
        if self.action == "login":
            success, msg, data = license_client.login(
                self.kwargs.get("email"),
                self.kwargs.get("password")
            )
            self.finished.emit(success, msg, data)
        elif self.action == "register":
            success, msg, data = license_client.register(
                self.kwargs.get("email"),
                self.kwargs.get("password"),
                self.kwargs.get("full_name")
            )
            self.finished.emit(success, msg, data)
        elif self.action == "verify":
            valid, msg, user = license_client.verify_current_session()
            self.finished.emit(valid, msg, user or {})

class AuthDialog(QDialog):
    auth_successful = pyqtSignal(dict)

    def __init__(self, parent=None, initial_message: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Dola AI - SaaS Licensing & Activation")
        self.setFixedSize(500, 620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet(AUTH_DIALOG_STYLE)
        
        self.initial_message = initial_message
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(16)

        # Header with Logo & Brand
        header_layout = QHBoxLayout()
        brand_icon = QLabel("✨")
        brand_icon.setFont(QFont("Segoe UI", 24))
        
        brand_info = QVBoxLayout()
        brand_title = QLabel("DOLA AI REMOVER")
        brand_title.setProperty("class", "title-label")
        brand_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        brand_sub = QLabel("Single-Device Cloud SaaS Licensing")
        brand_sub.setProperty("class", "sub-label")
        brand_info.addWidget(brand_title)
        brand_info.addWidget(brand_sub)
        
        header_layout.addWidget(brand_icon)
        header_layout.addLayout(brand_info)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_login_tab(), "Sign In")
        self.tabs.addTab(self._create_register_tab(), "Register Account")
        self.tabs.addTab(self._create_settings_tab(), "Settings / Device")
        main_layout.addWidget(self.tabs)

        # Hardware ID Footer pill
        hwid_layout = QHBoxLayout()
        hwid_lbl = QLabel(f"Device HWID: {license_client.hwid}")
        hwid_lbl.setFont(QFont("Consolas", 9))
        hwid_lbl.setStyleSheet("color: #6b7280;")
        
        copy_hwid_btn = QPushButton("Copy HWID")
        copy_hwid_btn.setProperty("class", "outline-btn")
        copy_hwid_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        copy_hwid_btn.clicked.connect(self._copy_hwid)
        
        hwid_layout.addWidget(hwid_lbl)
        hwid_layout.addStretch()
        hwid_layout.addWidget(copy_hwid_btn)
        main_layout.addLayout(hwid_layout)

        if self.initial_message:
            self._show_login_banner(self.initial_message, "warning")

    def _create_login_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Notice Banner (hidden by default)
        self.login_banner = QLabel()
        self.login_banner.setWordWrap(True)
        self.login_banner.hide()
        layout.addWidget(self.login_banner)

        # Email
        lbl_email = QLabel("Account Email:")
        lbl_email.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("name@domain.com")
        if license_client.user_data and license_client.user_data.get("email"):
            self.login_email.setText(license_client.user_data.get("email"))
        layout.addWidget(lbl_email)
        layout.addWidget(self.login_email)

        # Password
        lbl_pwd = QLabel("Password:")
        lbl_pwd.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.login_pwd = QLineEdit()
        self.login_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_pwd.setPlaceholderText("••••••••")
        self.login_pwd.returnPressed.connect(self._on_login_clicked)
        layout.addWidget(lbl_pwd)
        layout.addWidget(self.login_pwd)

        # Single Device info text
        device_note = QLabel("🔒 Single-device license: This login will bind your account to this PC.")
        device_note.setFont(QFont("Segoe UI", 8))
        device_note.setStyleSheet("color: #9ca3af; font-style: italic;")
        device_note.setWordWrap(True)
        layout.addWidget(device_note)

        layout.addStretch()

        # Submit Button
        self.login_btn = QPushButton("Sign In & Activate")
        self.login_btn.setProperty("class", "primary-btn")
        self.login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_btn.clicked.connect(self._on_login_clicked)
        layout.addWidget(self.login_btn)

        return widget

    def _create_register_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Notice Banner
        self.register_banner = QLabel()
        self.register_banner.setWordWrap(True)
        self.register_banner.hide()
        layout.addWidget(self.register_banner)

        # Full Name
        lbl_name = QLabel("Full Name / Nickname:")
        self.reg_name = QLineEdit()
        self.reg_name.setPlaceholderText("John Doe")
        layout.addWidget(lbl_name)
        layout.addWidget(self.reg_name)

        # Email
        lbl_email = QLabel("Email Address:")
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("john@example.com")
        layout.addWidget(lbl_email)
        layout.addWidget(self.reg_email)

        # Password
        lbl_pwd = QLabel("Password (Min 6 chars):")
        self.reg_pwd = QLineEdit()
        self.reg_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_pwd.setPlaceholderText("••••••••")
        layout.addWidget(lbl_pwd)
        layout.addWidget(self.reg_pwd)

        # Notice
        approval_note = QLabel("ℹ️ After registering, your account will be sent to the Super Admin for approval and activation.")
        approval_note.setFont(QFont("Segoe UI", 8))
        approval_note.setStyleSheet("color: #60a5fa;")
        approval_note.setWordWrap(True)
        layout.addWidget(approval_note)

        layout.addStretch()

        # Register Button
        self.reg_btn = QPushButton("Submit Registration")
        self.reg_btn.setProperty("class", "primary-btn")
        self.reg_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.reg_btn.clicked.connect(self._on_register_clicked)
        layout.addWidget(self.reg_btn)

        return widget

    def _create_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Server URL config
        lbl_server = QLabel("License Server Endpoint:")
        lbl_server.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.server_url_input = QLineEdit()
        self.server_url_input.setText(license_client.server_url)
        layout.addWidget(lbl_server)
        layout.addWidget(self.server_url_input)

        save_srv_btn = QPushButton("Save Server URL")
        save_srv_btn.setProperty("class", "outline-btn")
        save_srv_btn.clicked.connect(self._on_save_server_url)
        layout.addWidget(save_srv_btn)

        # Account details if cached
        layout.addSpacing(10)
        lbl_acc = QLabel("Current Session:")
        lbl_acc.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        layout.addWidget(lbl_acc)

        if license_client.user_data:
            u = license_client.user_data
            status_str = f"Account: {u.get('email', 'N/A')}\nStatus: {u.get('status', 'N/A').upper()}\nPlan: {license_client.get_plan_display()}"
            self.session_info_lbl = QLabel(status_str)
            self.session_info_lbl.setStyleSheet("background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; font-size: 12px;")
            layout.addWidget(self.session_info_lbl)

            logout_btn = QPushButton("Log Out & Clear Session")
            logout_btn.setProperty("class", "outline-btn")
            logout_btn.setStyleSheet("color: #fb7185; border-color: rgba(244,63,94,0.3);")
            logout_btn.clicked.connect(self._on_logout_clicked)
            layout.addWidget(logout_btn)
        else:
            no_acc_lbl = QLabel("No active session saved.")
            no_acc_lbl.setStyleSheet("color: #9ca3af; font-size: 12px;")
            layout.addWidget(no_acc_lbl)

        layout.addStretch()
        return widget

    def _show_login_banner(self, message: str, banner_type: str = "error"):
        self.login_banner.setText(message)
        self.login_banner.setProperty("class", f"banner-{banner_type}")
        self.login_banner.style().unpolish(self.login_banner)
        self.login_banner.style().polish(self.login_banner)
        self.login_banner.show()

    def _show_register_banner(self, message: str, banner_type: str = "error"):
        self.register_banner.setText(message)
        self.register_banner.setProperty("class", f"banner-{banner_type}")
        self.register_banner.style().unpolish(self.register_banner)
        self.register_banner.style().polish(self.register_banner)
        self.register_banner.show()

    def _copy_hwid(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(license_client.hwid)
        QMessageBox.information(self, "Copied", f"Hardware ID copied to clipboard:\n\n{license_client.hwid}")

    def _on_save_server_url(self):
        new_url = self.server_url_input.text().strip()
        if not new_url.startswith("http://") and not new_url.startswith("https://"):
            QMessageBox.warning(self, "Invalid URL", "Server URL must start with http:// or https://")
            return
        license_client.save_server_url(new_url)
        QMessageBox.information(self, "Saved", f"License Server URL updated to:\n{new_url}")

    def _on_logout_clicked(self):
        license_client.clear_session()
        QMessageBox.information(self, "Logged Out", "Session cleared successfully.")
        self.accept()

    def _on_login_clicked(self):
        email = self.login_email.text().strip()
        pwd = self.login_pwd.text().strip()
        
        if not email or "@" not in email:
            self._show_login_banner("Please enter a valid email address.", "error")
            return
        if not pwd:
            self._show_login_banner("Please enter your password.", "error")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Verifying License Online...")
        self.login_banner.hide()

        self.worker = AuthWorker("login", email=email, password=pwd)
        self.worker.finished.connect(self._handle_login_result)
        self.worker.start()

    def _handle_login_result(self, success: bool, msg: str, data: dict):
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In & Activate")

        if success:
            user_data = data.get("user", {})
            self._show_login_banner("✓ License verified! Launching application...", "success")
            self.auth_successful.emit(user_data)
            self.accept()
        else:
            error_code = data.get("error")
            if error_code == "pending_approval":
                self._show_login_banner("⏳ Account Pending Super Admin Approval\n\nYour account has been created but is waiting for the Super Admin to activate your subscription plan (7 days, 1 month, 1 year, or Lifetime). Please wait or contact administrator.", "warning")
            elif error_code == "device_mismatch":
                self._show_login_banner(f"🔒 Single-Device Restriction Violation\n\n{msg}", "error")
            elif error_code == "expired":
                self._show_login_banner("🛑 Subscription Expired\n\nYour license has expired. Please contact the administrator to renew.", "error")
            elif error_code == "suspended":
                self._show_login_banner("⏸️ Account Suspended\n\nYour account has been suspended by the administrator.", "error")
            else:
                self._show_login_banner(f"✕ {msg}", "error")

    def _on_register_clicked(self):
        name = self.reg_name.text().strip()
        email = self.reg_email.text().strip()
        pwd = self.reg_pwd.text().strip()

        if not name:
            self._show_register_banner("Please enter your full name or nickname.", "error")
            return
        if not email or "@" not in email:
            self._show_register_banner("Please enter a valid email address.", "error")
            return
        if len(pwd) < 6:
            self._show_register_banner("Password must be at least 6 characters.", "error")
            return

        self.reg_btn.setEnabled(False)
        self.reg_btn.setText("Submitting Registration...")
        self.register_banner.hide()

        self.worker = AuthWorker("register", email=email, password=pwd, full_name=name)
        self.worker.finished.connect(self._handle_register_result)
        self.worker.start()

    def _handle_register_result(self, success: bool, msg: str, data: dict):
        self.reg_btn.setEnabled(True)
        self.reg_btn.setText("Submit Registration")

        if success:
            self._show_register_banner("✓ Registration submitted successfully!\n\nYour account is now pending Super Admin approval. Once approved, you can sign in from the 'Sign In' tab.", "success")
            self.tabs.setCurrentIndex(0)
            self.login_email.setText(self.reg_email.text().strip())
            self._show_login_banner("Registration received! Waiting for Super Admin approval.", "warning")
        else:
            self._show_register_banner(f"✕ {msg}", "error")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = AuthDialog()
    dlg.show()
    sys.exit(app.exec())
