import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

from app.core.config import settings

SMTP_SERVER = settings.SMTP_SERVER
SMTP_PORT = settings.SMTP_PORT
SMTP_USERNAME = settings.SMTP_USERNAME
SMTP_PASSWORD = settings.SMTP_PASSWORD

def send_email(to_email: str, subject: str, body_text: str):
    """
    Sends an email using the configured SMTP server.
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"[Email Warning] SMTP credentials not set. Would have sent email to {to_email}: {subject}")
        return

    msg = EmailMessage()
    msg.set_content(body_text)
    msg["Subject"] = subject
    msg["From"] = SMTP_USERNAME
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[Email Success] Sent email to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[Email Error] Failed to send email to {to_email}: {e}")
        return False

