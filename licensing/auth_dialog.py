import sys
import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QWidget, QFrame, QMessageBox, QApplication, QSpacerItem,
    QSizePolicy, QGraphicsDropShadowEffect, QStackedWidget
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
    padding: 10px 20px;
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

QPushButton.link-btn {
    background: transparent;
    border: none;
    color: #818cf8;
    font-size: 12px;
    font-weight: 500;
    text-align: right;
    padding: 0;
}

QPushButton.link-btn:hover {
    color: #a5b4fc;
    text-decoration: underline;
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

class VerifyEmailDialog(QDialog):
    """Modal dialog to enter 6-digit email OTP verification code."""
    def __init__(self, email: str, parent=None):
        super().__init__(parent)
        self.email = email
        self.setWindowTitle("Verify Email Address")
        self.setFixedSize(420, 360)
        self.setStyleSheet(AUTH_DIALOG_STYLE)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        icon_lbl = QLabel("✉️")
        icon_lbl.setFont(QFont("Segoe UI", 26))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title = QLabel("Check Your Inbox")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(f"We sent a 6-digit verification code to:<br><b style='color:#6366f1;'>{self.email}</b>")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.hide()
        layout.addWidget(self.banner)

        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("Enter 6-Digit Code (e.g. 123456)")
        self.otp_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.otp_input.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
        self.otp_input.setMaxLength(6)
        self.otp_input.returnPressed.connect(self._verify)
        layout.addWidget(self.otp_input)

        self.verify_btn = QPushButton("Verify Code")
        self.verify_btn.setProperty("class", "primary-btn")
        self.verify_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.verify_btn.clicked.connect(self._verify)
        layout.addWidget(self.verify_btn)

        h_resend = QHBoxLayout()
        resend_btn = QPushButton("Resend Code")
        resend_btn.setProperty("class", "link-btn")
        resend_btn.clicked.connect(self._resend)
        h_resend.addStretch()
        h_resend.addWidget(resend_btn)
        h_resend.addStretch()
        layout.addLayout(h_resend)

    def _verify(self):
        otp = self.otp_input.text().strip()
        if len(otp) < 4:
            self._show_banner("Please enter the verification code.", "error")
            return
        self.verify_btn.setEnabled(False)
        success, msg = license_client.verify_email(self.email, otp)
        self.verify_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Email Verified", "✓ Email verified successfully!\n\nYour account is now pending Super Admin approval.")
            self.accept()
        else:
            self._show_banner(f"✕ {msg}", "error")

    def _resend(self):
        success, msg = license_client.resend_otp(self.email)
        if success:
            self._show_banner(f"✓ {msg}", "success")
        else:
            self._show_banner(f"✕ {msg}", "error")

    def _show_banner(self, msg, btype):
        self.banner.setText(msg)
        self.banner.setProperty("class", f"banner-{btype}")
        self.banner.style().unpolish(self.banner)
        self.banner.style().polish(self.banner)
        self.banner.show()

class ForgotPasswordDialog(QDialog):
    """Dialog for requesting and submitting password reset with OTP."""
    def __init__(self, parent=None, initial_email=""):
        super().__init__(parent)
        self.setWindowTitle("Reset Password")
        self.setFixedSize(440, 440)
        self.setStyleSheet(AUTH_DIALOG_STYLE)
        self.step = 1
        self.email = initial_email
        self._init_ui()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(12)

        self.title_lbl = QLabel("Forgot Password")
        self.title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.layout.addWidget(self.title_lbl)

        self.desc_lbl = QLabel("Enter your email address to receive a 6-digit password reset code.")
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("color: #9ca3af;")
        self.layout.addWidget(self.desc_lbl)

        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.hide()
        self.layout.addWidget(self.banner)

        # Step 1: Email Input
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email address")
        self.email_input.setText(self.email)
        self.layout.addWidget(self.email_input)

        # Step 2: OTP & New Password (Hidden initially)
        self.otp_label = QLabel("Enter 6-Digit Reset Code:")
        self.otp_label.hide()
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("e.g. 654321")
        self.otp_input.setMaxLength(6)
        self.otp_input.hide()

        self.pwd_label = QLabel("New Password (Min 6 chars):")
        self.pwd_label.hide()
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText("••••••••")
        self.pwd_input.hide()

        self.layout.addWidget(self.otp_label)
        self.layout.addWidget(self.otp_input)
        self.layout.addWidget(self.pwd_label)
        self.layout.addWidget(self.pwd_input)

        self.layout.addStretch()

        self.action_btn = QPushButton("Send Reset Code")
        self.action_btn.setProperty("class", "primary-btn")
        self.action_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.action_btn.clicked.connect(self._on_action_clicked)
        self.layout.addWidget(self.action_btn)

    def _on_action_clicked(self):
        if self.step == 1:
            email = self.email_input.text().strip()
            if not email or "@" not in email:
                self._show_banner("Please enter a valid email address.", "error")
                return
            self.email = email
            self.action_btn.setEnabled(False)
            success, msg = license_client.forgot_password(email)
            self.action_btn.setEnabled(True)

            self.step = 2
            self.title_lbl.setText("Enter Reset Code")
            self.desc_lbl.setText(f"We sent a 6-digit code to {email}.")
            self.email_input.setEnabled(False)
            self.otp_label.show()
            self.otp_input.show()
            self.pwd_label.show()
            self.pwd_input.show()
            self.action_btn.setText("Set New Password")
            self._show_banner(f"✓ {msg}", "success")
        else:
            otp = self.otp_input.text().strip()
            new_pwd = self.pwd_input.text().strip()
            if len(otp) < 4:
                self._show_banner("Please enter the 6-digit code.", "error")
                return
            if len(new_pwd) < 6:
                self._show_banner("New password must be at least 6 characters.", "error")
                return
            self.action_btn.setEnabled(False)
            success, msg = license_client.reset_password(self.email, otp, new_pwd)
            self.action_btn.setEnabled(True)
            if success:
                QMessageBox.information(self, "Password Reset", "✓ Password reset successfully!\n\nYou can now sign in with your new password.")
                self.accept()
            else:
                self._show_banner(f"✕ {msg}", "error")

    def _show_banner(self, msg, btype):
        self.banner.setText(msg)
        self.banner.setProperty("class", f"banner-{btype}")
        self.banner.style().unpolish(self.banner)
        self.banner.style().polish(self.banner)
        self.banner.show()

class AuthDialog(QDialog):
    auth_successful = pyqtSignal(dict)

    def __init__(self, parent=None, initial_message: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Dola AI — by Talha Shaikh")
        self.setFixedSize(500, 640)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet(AUTH_DIALOG_STYLE)
        
        self.initial_message = initial_message
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(26, 26, 26, 26)
        main_layout.setSpacing(14)

        # Header with Logo & Brand
        header_layout = QHBoxLayout()
        brand_icon = QLabel("✨")
        brand_icon.setFont(QFont("Segoe UI", 24))
        
        brand_info = QVBoxLayout()
        brand_title = QLabel("DOLA AI REMOVER")
        brand_title.setProperty("class", "title-label")
        brand_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        
        brand_sub = QLabel("Developed by <b>Talha Shaikh</b> &bull; <a href='https://talhashaikh.com' style='color:#a5b4fc; text-decoration:none;'>talhashaikh.com</a>")
        brand_sub.setTextFormat(Qt.TextFormat.RichText)
        brand_sub.setOpenExternalLinks(True)
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
        self.tabs.addTab(self._create_settings_tab(), "My Account")
        main_layout.addWidget(self.tabs)

        # Hardware ID & Creator Branding Footer
        footer_layout = QHBoxLayout()
        hwid_lbl = QLabel(f"Device HWID: {license_client.hwid}")
        hwid_lbl.setFont(QFont("Consolas", 8))
        hwid_lbl.setStyleSheet("color: #6b7280;")
        
        copy_hwid_btn = QPushButton("Copy HWID")
        copy_hwid_btn.setProperty("class", "outline-btn")
        copy_hwid_btn.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        copy_hwid_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        copy_hwid_btn.clicked.connect(self._copy_hwid)
        
        footer_layout.addWidget(hwid_lbl)
        footer_layout.addStretch()
        footer_layout.addWidget(copy_hwid_btn)
        main_layout.addLayout(footer_layout)

        # Website Credit link at bottom
        credit_lbl = QLabel("Official Website: <a href='https://talhashaikh.com' style='color:#6366f1; text-decoration:none; font-weight:bold;'>talhashaikh.com</a>")
        credit_lbl.setTextFormat(Qt.TextFormat.RichText)
        credit_lbl.setOpenExternalLinks(True)
        credit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit_lbl.setFont(QFont("Segoe UI", 9))
        main_layout.addWidget(credit_lbl)

        if self.initial_message:
            self._show_login_banner(self.initial_message, "warning")

    def _create_login_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Notice Banner
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

        # Forgot Password Link
        h_forgot = QHBoxLayout()
        forgot_btn = QPushButton("Forgot Password?")
        forgot_btn.setProperty("class", "link-btn")
        forgot_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        forgot_btn.clicked.connect(self._open_forgot_password)
        h_forgot.addStretch()
        h_forgot.addWidget(forgot_btn)
        layout.addLayout(h_forgot)

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
        layout.setSpacing(11)

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
        approval_note = QLabel("✉️ A 6-digit verification code will be sent to your email to verify your address.")
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

        lbl_acc = QLabel("Account & License Overview:")
        lbl_acc.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_acc.setStyleSheet("color: #6366f1;")
        layout.addWidget(lbl_acc)

        if license_client.user_data:
            u = license_client.user_data
            email = u.get("email", "N/A")
            full_name = u.get("full_name", "")
            status = u.get("status", "Active").upper()
            plan = license_client.get_plan_display()
            expires = u.get("expires_at", "Never (Lifetime)")
            if expires and "T" in str(expires):
                expires = str(expires).split("T")[0]
            
            info_html = f"""
            <div style='line-height: 1.6; font-size: 13px;'>
                <b>User:</b> {full_name} ({email})<br>
                <b>License Status:</b> <span style='color:#10b981; font-weight:bold;'>{status}</span><br>
                <b>Plan:</b> <span style='color:#a5b4fc; font-weight:bold;'>{plan}</span><br>
                <b>Expiry:</b> {expires}<br>
                <b>Device Locked:</b> Bound to this PC
            </div>
            """
            self.session_info_lbl = QLabel(info_html)
            self.session_info_lbl.setTextFormat(Qt.TextFormat.RichText)
            self.session_info_lbl.setStyleSheet(
                "background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); padding: 14px; border-radius: 8px;"
            )
            layout.addWidget(self.session_info_lbl)

            layout.addSpacing(8)
            logout_btn = QPushButton("Log Out & Clear Session")
            logout_btn.setProperty("class", "outline-btn")
            logout_btn.setStyleSheet("color: #fb7185; border-color: rgba(244,63,94,0.3); font-weight: 600;")
            logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            logout_btn.clicked.connect(self._on_logout_clicked)
            layout.addWidget(logout_btn)
        else:
            no_acc_card = QLabel(
                "<b>No Active Session</b><br><br>"
                "Sign in or register from the tabs above to activate this device."
            )
            no_acc_card.setTextFormat(Qt.TextFormat.RichText)
            no_acc_card.setStyleSheet(
                "background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); padding: 16px; border-radius: 8px; color: #9ca3af;"
            )
            layout.addWidget(no_acc_card)

        # Support note
        support_note = QLabel("💬 For subscription renewals, plan upgrades, or support, visit <a href='https://talhashaikh.com' style='color:#6366f1; text-decoration:none; font-weight:bold;'>talhashaikh.com</a>.")
        support_note.setTextFormat(Qt.TextFormat.RichText)
        support_note.setOpenExternalLinks(True)
        support_note.setFont(QFont("Segoe UI", 9))
        support_note.setStyleSheet("color: #6b7280; font-style: italic;")
        support_note.setWordWrap(True)
        layout.addWidget(support_note)

        layout.addStretch()
        return widget

    def _open_forgot_password(self):
        email = self.login_email.text().strip()
        dlg = ForgotPasswordDialog(self, initial_email=email)
        dlg.exec()

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
            if error_code == "email_not_verified":
                self._show_login_banner("✉️ Email Verification Required\n\nPlease verify your email code.", "warning")
                # Open verify email dialog
                v_dlg = VerifyEmailDialog(self.login_email.text().strip(), self)
                if v_dlg.exec() == QDialog.DialogCode.Accepted:
                    self._show_login_banner("✓ Email verified! Now awaiting Super Admin approval.", "warning")
            elif error_code == "pending_approval":
                self._show_login_banner("⏳ Account Pending Super Admin Approval\n\nYour account has been verified and is awaiting Super Admin activation. Please contact the administrator.", "warning")
            elif error_code == "device_mismatch":
                self._show_login_banner(f"🔒 Single-Device Restriction Violation\n\n{msg}", "error")
            elif error_code == "expired":
                self._show_login_banner("🛑 Subscription Expired\n\nYour license has expired. Visit talhashaikh.com to renew.", "error")
            elif error_code == "suspended":
                self._show_login_banner("⏸️ Account Suspended\n\nYour account has been suspended by administrator.", "error")
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
            email = self.reg_email.text().strip()
            # Open OTP verification dialog directly
            v_dlg = VerifyEmailDialog(email, self)
            v_dlg.exec()

            self.tabs.setCurrentIndex(0)
            self.login_email.setText(email)
            self._show_login_banner("Registration submitted! Once approved by Super Admin, you can sign in.", "warning")
        else:
            self._show_register_banner(f"✕ {msg}", "error")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = AuthDialog()
    dlg.show()
    sys.exit(app.exec())
