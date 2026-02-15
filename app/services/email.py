"""
Ekodi – Email service for verification, password reset, and notifications.
"""

import logging
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import get_settings

logger = logging.getLogger(__name__)


def _extract_email(from_str: str) -> str:
    """Extract bare email from 'Display Name <email>' format."""
    match = re.search(r'<([^>]+)>', from_str)
    if match:
        return match.group(1)
    return from_str.strip()


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

    # Envelope sender must be bare email (OVH and many SMTP servers reject display name format)
    envelope_from = _extract_email(settings.SMTP_FROM)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(envelope_from, to, msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
    except Exception as e:
        logger.error("Failed to send email to %s: %s – %s", to, subject, e)


def _email_header(settings) -> str:
    """Shared HTML header with Ekodi logo for all emails."""
    logo_url = f"{settings.BASE_URL}/logo-ekodi-std.png"
    return f"""
    <div style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;max-width:520px;margin:0 auto;padding:0;background:#09090b;border-radius:12px;overflow:hidden;">
        <!-- Header band -->
        <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16132b 100%);padding:28px 32px;text-align:center;border-bottom:1px solid #27272a;">
            <a href="{settings.BASE_URL}" style="text-decoration:none;" target="_blank">
                <img src="{logo_url}" alt="ekodi.ai" width="52" height="52"
                     style="display:inline-block;border-radius:12px;vertical-align:middle;" />
                <span style="display:inline-block;vertical-align:middle;margin-left:12px;font-size:26px;font-weight:700;color:#a78bfa;letter-spacing:-0.5px;">
                    ekodi<span style="color:#6d28d9;">.ai</span>
                </span>
            </a>
        </div>
        <!-- Body -->
        <div style="padding:32px;color:#e4e4e7;">
    """


_EMAIL_FOOTER = """
        </div>
        <!-- Footer -->
        <div style="padding:16px 32px;text-align:center;border-top:1px solid #27272a;">
            <p style="color:#52525b;font-size:11px;margin:0;">&copy; 2025 Ynnov &middot; ekodi.ai &mdash; Bamanankan AI Assistant</p>
        </div>
    </div>
    """


def send_verification_email(to: str, name: str, token: str):
    """Send email verification link."""
    settings = get_settings()
    verify_url = f"{settings.BASE_URL}/verify/{token}"
    html = f"""{_email_header(settings)}
            <h2 style="color:#fafafa;margin:0 0 8px;">Welcome, {name}!</h2>
            <p style="margin:0 0 24px;line-height:1.6;">
                Please verify your email address to activate your <strong>ekodi</strong> account.
            </p>
            <div style="text-align:center;margin:28px 0;">
                <a href="{verify_url}"
                   style="background:linear-gradient(135deg,#a78bfa,#6d28d9);color:white;padding:14px 36px;
                          border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
                    &#x2713;&ensp;Verify Email
                </a>
            </div>
            <p style="color:#71717a;font-size:12px;line-height:1.5;">
                If you did not create an account, you can safely ignore this email.
            </p>
            <p style="color:#52525b;font-size:11px;word-break:break-all;">
                {verify_url}
            </p>
    {_EMAIL_FOOTER}"""
    _send_email(to, "Verify your ekodi.ai account", html)


def send_password_reset_email(to: str, name: str, token: str):
    """Send password reset link."""
    settings = get_settings()
    reset_url = f"{settings.BASE_URL}/reset-password/{token}"
    html = f"""{_email_header(settings)}
            <h2 style="color:#fafafa;margin:0 0 8px;">Password Reset</h2>
            <p style="margin:0 0 24px;line-height:1.6;">
                Hi <strong>{name}</strong>, you requested a password reset.
                Click the button below to set a new password.
            </p>
            <div style="text-align:center;margin:28px 0;">
                <a href="{reset_url}"
                   style="background:linear-gradient(135deg,#a78bfa,#6d28d9);color:white;padding:14px 36px;
                          border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;display:inline-block;">
                    &#x1F512;&ensp;Reset Password
                </a>
            </div>
            <p style="color:#71717a;font-size:12px;line-height:1.5;">
                This link expires in 1 hour. If you didn&rsquo;t request this, ignore this email.
            </p>
            <p style="color:#52525b;font-size:11px;word-break:break-all;">
                {reset_url}
            </p>
    {_EMAIL_FOOTER}"""
    _send_email(to, "Reset your ekodi.ai password", html)


def send_account_deleted_email(to: str, name: str):
    """Send confirmation that account has been deleted."""
    settings = get_settings()
    html = f"""{_email_header(settings)}
            <h2 style="color:#fafafa;margin:0 0 8px;">Account Deleted</h2>
            <p style="margin:0 0 16px;line-height:1.6;">
                Hi <strong>{name}</strong>, your ekodi.ai account and all associated data
                have been permanently deleted.
            </p>
            <p style="line-height:1.6;">
                We&rsquo;re sorry to see you go. If you&rsquo;d like to come back, you&rsquo;re always welcome.
            </p>
            <p style="color:#71717a;font-size:12px;margin-top:24px;">
                This is an automated message. No reply needed.
            </p>
    {_EMAIL_FOOTER}"""
    _send_email(to, "Your ekodi.ai account has been deleted", html)
