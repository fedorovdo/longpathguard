from __future__ import annotations

import copy

from app import notifier
from app.settings import DEFAULT_CONFIG


class ApiRejectedResponse:
    def read(self) -> bytes:
        return b'{"ok": false}'

    def close(self) -> None:
        return None


class RefusingSmtp:
    def __init__(self, *_args, **_kwargs) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def starttls(self) -> None:
        return None

    def send_message(self, _message) -> dict:
        return {"recipient": (550, b"rejected")}


def test_telegram_api_rejection_is_delivery_failure(monkeypatch) -> None:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["telegram"].update({"enabled": True, "bot_token": "token", "chat_id": "123"})
    monkeypatch.setattr(
        notifier.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: ApiRejectedResponse(),
    )

    assert notifier.send_telegram("test", config).status == "delivery_failed"


def test_smtp_recipient_refusal_is_delivery_failure(monkeypatch) -> None:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["email"].update(
        {
            "enabled": True,
            "smtp_host": "smtp.example.test",
            "from_addr": "from@example.test",
            "to_addr": "to@example.test",
        }
    )
    monkeypatch.setattr(notifier.smtplib, "SMTP", RefusingSmtp)

    assert notifier.send_email("subject", "body", config).status == "delivery_failed"
