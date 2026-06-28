from __future__ import annotations

import json
import logging
import smtplib
import urllib.parse
import urllib.request
from dataclasses import dataclass
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

NOTIFICATION_STATUSES = {"success", "disabled", "missing_config", "delivery_failed"}


@dataclass(frozen=True)
class NotificationResult:
    provider: str
    status: str

    @property
    def success(self) -> bool:
        return self.status == "success"


def _allowed(severity: str, min_severity: str) -> bool:
    return SEVERITY_RANK.get(severity, 0) >= SEVERITY_RANK.get(min_severity, 4)


def send_telegram(message: str, config: dict[str, Any] | None = None) -> NotificationResult:
    active_config = config if config is not None else load_config()
    telegram = active_config.get("telegram", {})
    if not telegram.get("enabled"):
        return NotificationResult("telegram", "disabled")

    token = str(telegram.get("bot_token", "") or "").strip()
    chat_id = str(telegram.get("chat_id", "") or "").strip()
    if not token or not chat_id:
        return NotificationResult("telegram", "missing_config")

    try:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = urllib.request.urlopen(url, data=data, timeout=10)
        try:
            payload = json.loads(response.read().decode("utf-8"))
        finally:
            close = getattr(response, "close", None)
            if close:
                close()
        if not payload.get("ok"):
            logging.error("Telegram delivery failed (ApiRejected)")
            return NotificationResult("telegram", "delivery_failed")
        return NotificationResult("telegram", "success")
    except Exception as exc:
        logging.error("Telegram delivery failed (%s)", type(exc).__name__)
        return NotificationResult("telegram", "delivery_failed")


def send_email(
    subject: str,
    body: str,
    config: dict[str, Any] | None = None,
) -> NotificationResult:
    active_config = config if config is not None else load_config()
    email = active_config.get("email", {})
    if not email.get("enabled"):
        return NotificationResult("email", "disabled")

    required = ("smtp_host", "from_addr", "to_addr")
    if any(not str(email.get(key, "") or "").strip() for key in required):
        return NotificationResult("email", "missing_config")
    try:
        smtp_port = int(email.get("smtp_port", 587))
    except (TypeError, ValueError):
        return NotificationResult("email", "missing_config")
    if not 1 <= smtp_port <= 65535:
        return NotificationResult("email", "missing_config")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email.get("from_addr")
    message["To"] = email.get("to_addr")
    message.set_content(body)

    try:
        with smtplib.SMTP(email.get("smtp_host"), smtp_port, timeout=10) as smtp:
            if email.get("use_tls", True):
                smtp.starttls()
            if email.get("smtp_user"):
                smtp.login(email.get("smtp_user"), email.get("smtp_password", ""))
            refused = smtp.send_message(message)
        if refused:
            logging.error("Email delivery failed (RecipientsRefused)")
            return NotificationResult("email", "delivery_failed")
        return NotificationResult("email", "success")
    except Exception as exc:
        logging.error("Email delivery failed (%s)", type(exc).__name__)
        return NotificationResult("email", "delivery_failed")


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
        send_telegram(text, config)

    email = config.get("email", {})
    if email.get("enabled") and _allowed(severity, email.get("min_severity", "critical")):
        send_email(f"LongPathGuard {severity}", text, config)
