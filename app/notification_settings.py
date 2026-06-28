from __future__ import annotations

from collections.abc import Mapping
from typing import Any

NOTIFICATION_SEVERITIES = (
    "warning",
    "long_name",
    "danger",
    "critical",
    "critical_long_name",
)


def _text(form: Mapping[str, Any], key: str) -> str:
    return str(form.get(key, "") or "").strip()


def update_notification_config(config: dict[str, Any], form: Mapping[str, Any]) -> str | None:
    telegram = config.setdefault("telegram", {})
    existing_token = str(telegram.get("bot_token", "") or "")
    submitted_token = _text(form, "telegram_bot_token")
    if form.get("clear_telegram_bot_token") == "on":
        bot_token = ""
    elif submitted_token:
        bot_token = submitted_token
    else:
        bot_token = existing_token

    telegram_min_severity = _text(form, "telegram_min_severity") or "critical"
    if telegram_min_severity not in NOTIFICATION_SEVERITIES:
        return "notification_severity_invalid"

    telegram.update(
        {
            "enabled": form.get("telegram_enabled") == "on",
            "bot_token": bot_token,
            "chat_id": _text(form, "telegram_chat_id"),
            "min_severity": telegram_min_severity,
        }
    )

    email = config.setdefault("email", {})
    existing_password = str(email.get("smtp_password", "") or "")
    submitted_password = _text(form, "email_smtp_password")
    if form.get("clear_email_smtp_password") == "on":
        smtp_password = ""
    elif submitted_password:
        smtp_password = submitted_password
    else:
        smtp_password = existing_password

    try:
        smtp_port = int(_text(form, "email_smtp_port"))
    except (TypeError, ValueError):
        return "email_smtp_port_invalid"
    if not 1 <= smtp_port <= 65535:
        return "email_smtp_port_invalid"

    email_min_severity = _text(form, "email_min_severity") or "critical"
    if email_min_severity not in NOTIFICATION_SEVERITIES:
        return "notification_severity_invalid"

    email.update(
        {
            "enabled": form.get("email_enabled") == "on",
            "smtp_host": _text(form, "email_smtp_host"),
            "smtp_port": smtp_port,
            "smtp_user": _text(form, "email_smtp_user"),
            "smtp_password": smtp_password,
            "from_addr": _text(form, "email_from_addr"),
            "to_addr": _text(form, "email_to_addr"),
            "use_tls": form.get("email_use_tls") == "on",
            "min_severity": email_min_severity,
        }
    )

    if telegram["enabled"]:
        if not telegram["bot_token"]:
            return "telegram_token_required"
        if not telegram["chat_id"]:
            return "telegram_chat_id_required"

    if email["enabled"]:
        if not email["smtp_host"]:
            return "email_smtp_host_required"
        if not email["from_addr"]:
            return "email_from_addr_required"
        if not email["to_addr"]:
            return "email_to_addr_required"

    return None
