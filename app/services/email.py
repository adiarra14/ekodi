"""
Ekodi – Email service for verification, password reset, and notifications.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import get_settings

logger = logging.getLogger(__name__)


def _send_email(to: str, subject: str, html_body: str):
    """Send an email via SMTP. Silently logs errors if SMTP is not configured."""
    settings = get_settings()

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured – email to %s NOT sent: %s", to, subject)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to, msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)


def send_verification_email(to: str, name: str, token: str):
    """Send email verification link."""
    settings = get_settings()
    verify_url = f"{settings.BASE_URL}/verify/{token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:0 auto;padding:32px;background:#09090b;color:#e4e4e7;border-radius:12px;">
        <div style="text-align:center;margin-bottom:24px;">
            <h1 style="color:#a78bfa;margin:0;">ekodi.ai</h1>
        </div>
        <h2 style="color:#fafafa;">Welcome, {name}!</h2>
        <p>Please verify your email address to activate your ekodi account.</p>
        <div style="text-align:center;margin:32px 0;">
            <a href="{verify_url}" style="background:linear-gradient(135deg,#a78bfa,#6d28d9);color:white;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;">
                Verify Email
            </a>
        </div>
        <p style="color:#71717a;font-size:12px;">If you did not create an account, you can ignore this email.</p>
        <p style="color:#71717a;font-size:12px;">Link: {verify_url}</p>
    </div>
    """
    _send_email(to, "Verify your ekodi.ai account", html)


def send_password_reset_email(to: str, name: str, token: str):
    """Send password reset link."""
    settings = get_settings()
    reset_url = f"{settings.BASE_URL}/reset-password/{token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:0 auto;padding:32px;background:#09090b;color:#e4e4e7;border-radius:12px;">
        <div style="text-align:center;margin-bottom:24px;">
            <h1 style="color:#a78bfa;margin:0;">ekodi.ai</h1>
        </div>
        <h2 style="color:#fafafa;">Password Reset</h2>
        <p>Hi {name}, you requested a password reset. Click the button below to set a new password.</p>
        <div style="text-align:center;margin:32px 0;">
            <a href="{reset_url}" style="background:linear-gradient(135deg,#a78bfa,#6d28d9);color:white;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;">
                Reset Password
            </a>
        </div>
        <p style="color:#71717a;font-size:12px;">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
        <p style="color:#71717a;font-size:12px;">Link: {reset_url}</p>
    </div>
    """
    _send_email(to, "Reset your ekodi.ai password", html)


def send_account_deleted_email(to: str, name: str):
    """Send confirmation that account has been deleted."""
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:0 auto;padding:32px;background:#09090b;color:#e4e4e7;border-radius:12px;">
        <div style="text-align:center;margin-bottom:24px;">
            <h1 style="color:#a78bfa;margin:0;">ekodi.ai</h1>
        </div>
        <h2 style="color:#fafafa;">Account Deleted</h2>
        <p>Hi {name}, your ekodi.ai account and all associated data have been permanently deleted.</p>
        <p>We're sorry to see you go. If you'd like to come back, you're always welcome.</p>
        <p style="color:#71717a;font-size:12px;">This is an automated message. No reply needed.</p>
    </div>
    """
    _send_email(to, "Your ekodi.ai account has been deleted", html)
