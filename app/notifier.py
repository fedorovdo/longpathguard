from __future__ import annotations

import logging
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage
from typing import Any

from .settings import load_config

SEVERITY_RANK = {
    "ok": 0,
    "warning": 1,
    "long_name": 2,
    "danger": 3,
    "critical": 4,
    "critical_long_name": 5,
}


def _allowed(severity: str, min_severity: str) -> bool:
    return SEVERITY_RANK.get(severity, 0) >= SEVERITY_RANK.get(min_severity, 4)


def send_telegram(message: str) -> None:
    config = load_config()
    telegram = config.get("telegram", {})
    if not telegram.get("enabled"):
        return
    token = telegram.get("bot_token")
    chat_id = telegram.get("chat_id")
    if not token or not chat_id:
        return

    try:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        urllib.request.urlopen(url, data=data, timeout=10).read()
    except Exception:
        logging.exception("Telegram notification failed")


def send_email(subject: str, body: str) -> None:
    config = load_config()
    email = config.get("email", {})
    if not email.get("enabled"):
        return
    required = ["smtp_host", "from_addr", "to_addr"]
    if any(not email.get(key) for key in required):
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email.get("from_addr")
    message["To"] = email.get("to_addr")
    message.set_content(body)

    try:
        with smtplib.SMTP(email.get("smtp_host"), int(email.get("smtp_port", 587)), timeout=10) as smtp:
            if email.get("use_tls", True):
                smtp.starttls()
            if email.get("smtp_user"):
                smtp.login(email.get("smtp_user"), email.get("smtp_password", ""))
            smtp.send_message(message)
    except Exception:
        logging.exception("Email notification failed")


def notify_event(event: dict[str, Any]) -> None:
    config = load_config()
    severity = event.get("severity", "ok")
    text = (
        f"LongPathGuard: {severity}\n"
        f"Event: {event.get('event_type')}\n"
        f"Path length: {event.get('full_path_length')}\n"
        f"Name length: {event.get('name_length')}\n"
        f"Path: {event.get('full_path')}"
    )

    telegram = config.get("telegram", {})
    if telegram.get("enabled") and _allowed(severity, telegram.get("min_severity", "critical")):
        send_telegram(text)

    email = config.get("email", {})
    if email.get("enabled") and _allowed(severity, email.get("min_severity", "critical")):
        send_email(f"LongPathGuard {severity}", text)
