from __future__ import annotations

import copy

import pytest

from app.notification_settings import update_notification_config
from app.settings import DEFAULT_CONFIG


def base_form(config: dict) -> dict[str, str]:
    return {
        "telegram_bot_token": "",
        "telegram_chat_id": str(config["telegram"].get("chat_id", "")),
        "telegram_min_severity": str(config["telegram"].get("min_severity", "critical")),
        "email_smtp_host": str(config["email"].get("smtp_host", "")),
        "email_smtp_port": str(config["email"].get("smtp_port", 587)),
        "email_smtp_user": str(config["email"].get("smtp_user", "")),
        "email_smtp_password": "",
        "email_from_addr": str(config["email"].get("from_addr", "")),
        "email_to_addr": str(config["email"].get("to_addr", "")),
        "email_min_severity": str(config["email"].get("min_severity", "critical")),
    }


def make_config() -> dict:
    return copy.deepcopy(DEFAULT_CONFIG)


def test_saves_telegram_non_secret_fields() -> None:
    config = make_config()
    config["telegram"]["bot_token"] = "saved-token"
    form = base_form(config)
    form.update(
        {
            "telegram_enabled": "on",
            "telegram_chat_id": "-100123456",
            "telegram_min_severity": "danger",
        }
    )

    assert update_notification_config(config, form) is None
    assert config["telegram"]["enabled"] is True
    assert config["telegram"]["chat_id"] == "-100123456"
    assert config["telegram"]["min_severity"] == "danger"


def test_saves_email_non_secret_fields() -> None:
    config = make_config()
    config["email"]["smtp_password"] = "saved-password"
    form = base_form(config)
    form.update(
        {
            "email_enabled": "on",
            "email_smtp_host": "smtp.example.test",
            "email_smtp_port": "465",
            "email_smtp_user": "mailer",
            "email_from_addr": "from@example.test",
            "email_to_addr": "to@example.test",
            "email_use_tls": "on",
            "email_min_severity": "warning",
        }
    )

    assert update_notification_config(config, form) is None
    assert config["email"]["enabled"] is True
    assert config["email"]["smtp_host"] == "smtp.example.test"
    assert config["email"]["smtp_port"] == 465
    assert config["email"]["smtp_user"] == "mailer"
    assert config["email"]["from_addr"] == "from@example.test"
    assert config["email"]["to_addr"] == "to@example.test"
    assert config["email"]["use_tls"] is True
    assert config["email"]["min_severity"] == "warning"


def test_blank_token_preserves_existing_token() -> None:
    config = make_config()
    config["telegram"]["bot_token"] = "saved-token"

    assert update_notification_config(config, base_form(config)) is None
    assert config["telegram"]["bot_token"] == "saved-token"


def test_blank_password_preserves_existing_password() -> None:
    config = make_config()
    config["email"]["smtp_password"] = "saved-password"

    assert update_notification_config(config, base_form(config)) is None
    assert config["email"]["smtp_password"] == "saved-password"


def test_explicitly_clears_telegram_token() -> None:
    config = make_config()
    config["telegram"]["bot_token"] = "saved-token"
    form = base_form(config)
    form["clear_telegram_bot_token"] = "on"

    assert update_notification_config(config, form) is None
    assert config["telegram"]["bot_token"] == ""


def test_explicitly_clears_smtp_password() -> None:
    config = make_config()
    config["email"]["smtp_password"] = "saved-password"
    form = base_form(config)
    form["clear_email_smtp_password"] = "on"

    assert update_notification_config(config, form) is None
    assert config["email"]["smtp_password"] == ""


@pytest.mark.parametrize(
    ("token", "chat_id", "expected"),
    [
        ("", "123", "telegram_token_required"),
        ("token", "", "telegram_chat_id_required"),
    ],
)
def test_rejects_incomplete_enabled_telegram(token: str, chat_id: str, expected: str) -> None:
    config = make_config()
    config["telegram"]["bot_token"] = token
    form = base_form(config)
    form.update({"telegram_enabled": "on", "telegram_chat_id": chat_id})

    assert update_notification_config(config, form) == expected


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("email_smtp_host", "email_smtp_host_required"),
        ("email_from_addr", "email_from_addr_required"),
        ("email_to_addr", "email_to_addr_required"),
    ],
)
def test_rejects_incomplete_enabled_email(field: str, expected: str) -> None:
    config = make_config()
    form = base_form(config)
    form.update(
        {
            "email_enabled": "on",
            "email_smtp_host": "smtp.example.test",
            "email_from_addr": "from@example.test",
            "email_to_addr": "to@example.test",
        }
    )
    form[field] = ""

    assert update_notification_config(config, form) == expected


@pytest.mark.parametrize("port", ["", "zero", "0", "65536"])
def test_rejects_invalid_smtp_ports(port: str) -> None:
    config = make_config()
    form = base_form(config)
    form["email_smtp_port"] = port

    assert update_notification_config(config, form) == "email_smtp_port_invalid"
