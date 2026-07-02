import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load from .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

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

