import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.titan.email")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "info@talhashaikh.com")
SMTP_PASS = os.getenv("SMTP_PASS", "9NR47Q6/w")
BRAND_NAME = "Talha Shaikh"
BRAND_URL = "https://talhashaikh.com"
APP_NAME = "Dola AI Watermark Remover"

def _send_email(to_email: str, subject: str, html_content: str, text_content: str = "") -> bool:
    """Send an HTML email via Titan SMTP SSL."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{BRAND_NAME} <{SMTP_USER}>"
        msg["To"] = to_email

        if text_content:
            part1 = MIMEText(text_content, "plain")
            msg.attach(part1)

        part2 = MIMEText(html_content, "html")
        msg.attach(part2)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=15) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"[EMAIL] Sent '{subject}' to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        return False

def send_verification_email(to_email: str, full_name: str, otp_code: str) -> bool:
    """Send 6-digit OTP email verification."""
    subject = f"{otp_code} is your {APP_NAME} Verification Code"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #0b0f19; margin: 0; padding: 20px; color: #f3f4f6; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #111827; border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; padding: 36px; }}
            .brand-header {{ text-align: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 20px; margin-bottom: 24px; }}
            .brand-title {{ font-size: 20px; font-weight: 800; color: #6366f1; letter-spacing: 0.5px; margin: 0; }}
            .brand-sub {{ font-size: 12px; color: #9ca3af; margin-top: 4px; }}
            .greeting {{ font-size: 16px; font-weight: 600; color: #ffffff; margin-bottom: 14px; }}
            .text {{ font-size: 14px; color: #d1d5db; line-height: 1.6; margin-bottom: 20px; }}
            .otp-box {{ background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(79,70,229,0.25)); border: 1px solid #6366f1; border-radius: 10px; padding: 18px; text-align: center; margin: 24px 0; }}
            .otp-code {{ font-family: 'Courier New', monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #ffffff; margin: 0; }}
            .expiry-note {{ font-size: 12px; color: #f59e0b; margin-top: 8px; }}
            .footer {{ text-align: center; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 20px; margin-top: 28px; font-size: 12px; color: #6b7280; }}
            .footer a {{ color: #6366f1; text-decoration: none; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="brand-header">
                <h1 class="brand-title">{APP_NAME}</h1>
                <div class="brand-sub">Developed by <a href="{BRAND_URL}" style="color:#a5b4fc; text-decoration:none; font-weight:bold;">{BRAND_NAME}</a></div>
            </div>
            
            <div class="greeting">Hello {full_name or 'there'},</div>
            <div class="text">
                Thank you for registering for <b>{APP_NAME}</b>. Please use the verification code below to verify your email address and activate your account request:
            </div>
            
            <div class="otp-box">
                <div class="otp-code">{otp_code}</div>
                <div class="expiry-note">⏱️ Code expires in 15 minutes</div>
            </div>
            
            <div class="text" style="font-size: 13px; color: #9ca3af;">
                If you did not register for an account, please ignore this email.
            </div>
            
            <div class="footer">
                &copy; 2026 <b>{BRAND_NAME}</b> &bull; <a href="{BRAND_URL}">talhashaikh.com</a><br>
                For support, contact <a href="mailto:{SMTP_USER}">{SMTP_USER}</a>
            </div>
        </div>
    </body>
    </html>
    """
    return _send_email(to_email, subject, html, f"Your verification code is: {otp_code}")

def send_password_reset_email(to_email: str, full_name: str, otp_code: str) -> bool:
    """Send 6-digit OTP password reset code."""
    subject = f"{otp_code} is your {APP_NAME} Password Reset Code"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #0b0f19; margin: 0; padding: 20px; color: #f3f4f6; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #111827; border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; padding: 36px; }}
            .brand-header {{ text-align: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 20px; margin-bottom: 24px; }}
            .brand-title {{ font-size: 20px; font-weight: 800; color: #f43f5e; letter-spacing: 0.5px; margin: 0; }}
            .brand-sub {{ font-size: 12px; color: #9ca3af; margin-top: 4px; }}
            .greeting {{ font-size: 16px; font-weight: 600; color: #ffffff; margin-bottom: 14px; }}
            .text {{ font-size: 14px; color: #d1d5db; line-height: 1.6; margin-bottom: 20px; }}
            .otp-box {{ background: linear-gradient(135deg, rgba(244,63,94,0.15), rgba(225,29,72,0.25)); border: 1px solid #f43f5e; border-radius: 10px; padding: 18px; text-align: center; margin: 24px 0; }}
            .otp-code {{ font-family: 'Courier New', monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #ffffff; margin: 0; }}
            .expiry-note {{ font-size: 12px; color: #fbbf24; margin-top: 8px; }}
            .footer {{ text-align: center; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 20px; margin-top: 28px; font-size: 12px; color: #6b7280; }}
            .footer a {{ color: #6366f1; text-decoration: none; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="brand-header">
                <h1 class="brand-title">Password Reset Request</h1>
                <div class="brand-sub">{APP_NAME} &bull; by <a href="{BRAND_URL}" style="color:#a5b4fc; text-decoration:none; font-weight:bold;">{BRAND_NAME}</a></div>
            </div>
            
            <div class="greeting">Hello {full_name or 'there'},</div>
            <div class="text">
                We received a request to reset your password for <b>{APP_NAME}</b>. Enter the 6-digit code below in the application to choose a new password:
            </div>
            
            <div class="otp-box">
                <div class="otp-code">{otp_code}</div>
                <div class="expiry-note">⏱️ Code expires in 15 minutes</div>
            </div>
            
            <div class="text" style="font-size: 13px; color: #9ca3af;">
                If you did not request a password reset, your account is safe and you can safely ignore this email.
            </div>
            
            <div class="footer">
                &copy; 2026 <b>{BRAND_NAME}</b> &bull; <a href="{BRAND_URL}">talhashaikh.com</a><br>
                For support, contact <a href="mailto:{SMTP_USER}">{SMTP_USER}</a>
            </div>
        </div>
    </body>
    </html>
    """
    return _send_email(to_email, subject, html, f"Your password reset code is: {otp_code}")
