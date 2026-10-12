import os
import re
import smtplib
import ssl
import time
from collections import deque
from email.message import EmailMessage
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import BadRequest
from werkzeug.middleware.proxy_fix import ProxyFix


BASE_DIR = Path(__file__).resolve().parent
RECIPIENT = "worldbbc@gmail.com"
REQUEST_TYPES = {
    "Website development",
    "IT management or support",
    "Something else",
}
EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)
RATE_LIMIT_WINDOW_SECONDS = 600
RATE_LIMIT_MAX_REQUESTS = 5
SMTP_TIMEOUT_SECONDS = 20
RATE_LIMITS: dict[str, deque[float]] = {}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/styles.css")
def stylesheet():
    return send_from_directory(BASE_DIR, "styles.css")


@app.get("/script.js")
def javascript():
    return send_from_directory(BASE_DIR, "script.js")


@app.get("/healthz")
def health_check():
    return jsonify(status="ok")


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="The request is too large."), 413


@app.errorhandler(500)
def internal_server_error(_error):
    return jsonify(error="The message service encountered an unexpected error."), 500


def _clean_text(value, field, max_length):
    if not isinstance(value, str):
        return None, f"Please provide your {field}."

    cleaned = value.strip()
    if not cleaned:
        return None, f"Please provide your {field}."
    if len(cleaned) > max_length:
        return None, f"Your {field} must be {max_length} characters or fewer."

    return cleaned, None


def _rate_limit_response(client_ip):
    now = time.monotonic()
    for address, attempts in list(RATE_LIMITS.items()):
        while attempts and now - attempts[0] >= RATE_LIMIT_WINDOW_SECONDS:
            attempts.popleft()
        if not attempts:
            del RATE_LIMITS[address]

    attempts = RATE_LIMITS.setdefault(client_ip, deque())
    if len(attempts) >= RATE_LIMIT_MAX_REQUESTS:
        retry_after = max(1, int(RATE_LIMIT_WINDOW_SECONDS - (now - attempts[0])))
        return jsonify(error="Too many messages. Please wait a few minutes and try again."), 429, {
            "Retry-After": str(retry_after)
        }

    attempts.append(now)
    return None


@app.post("/api/contact")
def submit_contact():
    if not request.is_json:
        return jsonify(error="Send the form as JSON."), 415

    try:
        data = request.get_json()
    except BadRequest:
        return jsonify(error="The submitted form data is not valid JSON."), 400

    if not isinstance(data, dict):
        return jsonify(error="The submitted form data must be an object."), 400

    if data.get("website"):
        return jsonify(error="The message could not be accepted."), 400

    name, error = _clean_text(data.get("name"), "name", 120)
    if error:
        return jsonify(error=error), 400

    email, error = _clean_text(data.get("email"), "email address", 254)
    if error or not EMAIL_PATTERN.fullmatch(email):
        return jsonify(error="Please enter a valid email address."), 400

    inquiry_type, error = _clean_text(data.get("request"), "request type", 80)
    if error or inquiry_type not in REQUEST_TYPES:
        return jsonify(error="Please select a valid request type."), 400

    message, error = _clean_text(data.get("message"), "message", 5000)
    if error:
        return jsonify(error=error), 400

    client_ip = request.remote_addr
    if not client_ip:
        app.logger.error("Contact form request did not include a client IP address.")
        return jsonify(error="The message service is temporarily unavailable."), 503

    rate_limit_response = _rate_limit_response(client_ip)
    if rate_limit_response:
        return rate_limit_response

    app_password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    if not app_password:
        app.logger.error("The GMAIL_APP_PASSWORD environment variable is not configured.")
        return jsonify(error="The message service is not configured yet. Please try again later."), 503

    email_message = EmailMessage()
    email_message["Subject"] = f"Portfolio inquiry: {inquiry_type}"
    email_message["From"] = RECIPIENT
    email_message["To"] = RECIPIENT
    email_message["Reply-To"] = email
    email_message.set_content(
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Request: {inquiry_type}\n\n"
        f"{message}"
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            smtp.login(RECIPIENT, app_password)
            refused_recipients = smtp.send_message(email_message)
            if refused_recipients:
                raise smtplib.SMTPRecipientsRefused(refused_recipients)
    except (OSError, smtplib.SMTPException):
        app.logger.exception("Unable to deliver a portfolio inquiry by email.")
        return jsonify(error="Your message could not be sent right now. Please try again later."), 502

    return jsonify(message="Your message has been sent."), 200
