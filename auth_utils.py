import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode

from flask import flash


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def sanitize_text(value):
    return re.sub(r"<[^>]+>", "", str(value or "")).strip()


def validate_email(email):
    if not email:
        return "Email is required."
    if not EMAIL_PATTERN.match(email.strip()):
        return "Please enter a valid email address."
    return None


def validate_password(password):
    if not password:
        return "Password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must include at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must include at least one lowercase letter."
    if not re.search(r"\d", password):
        return "Password must include at least one number."
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must include at least one special character."
    return None


def get_password_strength(password):
    if not password:
        return {"label": "Enter a password", "score": 0}
    score = 0
    if len(password) >= 8:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[^A-Za-z0-9]", password):
        score += 1
    if score <= 2:
        return {"label": "Weak", "score": score}
    if score <= 4:
        return {"label": "Strong", "score": score}
    return {"label": "Excellent", "score": score}


def build_google_oauth_url(base_url, client_id, redirect_uri, state):
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def send_email(to_email, subject, body):
    smtp_server = os.getenv("MAIL_SERVER")
    smtp_port = os.getenv("MAIL_PORT", "587")
    smtp_username = os.getenv("MAIL_USERNAME")
    smtp_password = os.getenv("MAIL_PASSWORD")
    sender_email = os.getenv("MAIL_FROM", smtp_username or "noreply@nutriscan.ai")

    if not smtp_server:
        print(f"[MAIL] {subject}\nTo: {to_email}\n{body}")
        return True

    try:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = to_email
        message.set_content(body)

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            if os.getenv("MAIL_USE_TLS", "true").lower() == "true":
                server.starttls(context=context)
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.send_message(message)
        return True
    except Exception as exc:
        print(f"Email send failed: {exc}")
        return False
