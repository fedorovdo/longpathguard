from __future__ import annotations

import copy
import logging

from app import notifier
from app.settings import DEFAULT_CONFIG


class TelegramResponse:
    def read(self) -> bytes:
        return b'{"ok": true}'

    def close(self) -> None:
        return None


class FakeSmtp:
    def __init__(self, *_args, **_kwargs) -> None:
        self.sent = False

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, _username, _password) -> None:
        return None

    def send_message(self, _message) -> None:
        self.sent = True


def make_config() -> dict:
    return copy.deepcopy(DEFAULT_CONFIG)


def test_telegram_result_distinguishes_disabled_and_missing_config() -> None:
    config = make_config()
    assert notifier.send_telegram("test", config).status == "disabled"

    config["telegram"]["enabled"] = True
    assert notifier.send_telegram("test", config).status == "missing_config"


def test_telegram_result_handles_success(monkeypatch) -> None:
    config = make_config()
    config["telegram"].update({"enabled": True, "bot_token": "token", "chat_id": "123"})
    monkeypatch.setattr(notifier.urllib.request, "urlopen", lambda *_args, **_kwargs: TelegramResponse())

    result = notifier.send_telegram("test", config)

    assert result.status == "success"
    assert result.success is True


def test_telegram_failure_does_not_log_token(monkeypatch, caplog) -> None:
    config = make_config()
    secret = "never-log-this-token"
    config["telegram"].update({"enabled": True, "bot_token": secret, "chat_id": "123"})

    def fail(*_args, **_kwargs):
        raise OSError(f"request failed for {secret}")

    monkeypatch.setattr(notifier.urllib.request, "urlopen", fail)
    with caplog.at_level(logging.ERROR):
        result = notifier.send_telegram("test", config)

    assert result.status == "delivery_failed"
    assert secret not in caplog.text


def test_email_result_distinguishes_disabled_and_missing_config() -> None:
    config = make_config()
    assert notifier.send_email("subject", "body", config).status == "disabled"

    config["email"]["enabled"] = True
    assert notifier.send_email("subject", "body", config).status == "missing_config"


def test_email_result_handles_success(monkeypatch) -> None:
    config = make_config()
    config["email"].update(
        {
            "enabled": True,
            "smtp_host": "smtp.example.test",
            "from_addr": "from@example.test",
            "to_addr": "to@example.test",
        }
    )
    monkeypatch.setattr(notifier.smtplib, "SMTP", FakeSmtp)

    result = notifier.send_email("subject", "body", config)

    assert result.status == "success"


def test_email_failure_does_not_log_password(monkeypatch, caplog) -> None:
    config = make_config()
    secret = "never-log-this-password"
    config["email"].update(
        {
            "enabled": True,
            "smtp_host": "smtp.example.test",
            "smtp_user": "mailer",
            "smtp_password": secret,
            "from_addr": "from@example.test",
            "to_addr": "to@example.test",
        }
    )

    class FailingSmtp:
        def __init__(self, *_args, **_kwargs) -> None:
            raise OSError(f"connection failed with {secret}")

    monkeypatch.setattr(notifier.smtplib, "SMTP", FailingSmtp)
    with caplog.at_level(logging.ERROR):
        result = notifier.send_email("subject", "body", config)

    assert result.status == "delivery_failed"
    assert secret not in caplog.text
