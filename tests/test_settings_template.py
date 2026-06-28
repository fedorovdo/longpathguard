from __future__ import annotations

import copy
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.notification_settings import NOTIFICATION_SEVERITIES
from app.settings import DEFAULT_CONFIG


def test_settings_html_never_renders_saved_secrets() -> None:
    config = copy.deepcopy(DEFAULT_CONFIG)
    telegram_secret = "telegram-secret-must-not-render"
    email_secret = "email-secret-must-not-render"
    config["telegram"]["bot_token"] = telegram_secret
    config["email"]["smtp_password"] = email_secret

    environment = Environment(
        loader=FileSystemLoader("app/templates"),
        autoescape=select_autoescape(("html",)),
    )
    environment.globals["url_for"] = lambda *_args, **_kwargs: "/static/style.css"
    template = environment.get_template("settings.html")
    request = SimpleNamespace(url=SimpleNamespace(path="/settings"))

    html = template.render(
        request=request,
        language="en",
        t=lambda key: key,
        config=config,
        saved=False,
        error_code=None,
        notice_code=None,
        notice_success=False,
        notification_severity_values=NOTIFICATION_SEVERITIES,
        telegram_secret_configured=True,
        telegram_test_ready=False,
        email_secret_configured=True,
        email_test_ready=False,
    )

    assert telegram_secret not in html
    assert email_secret not in html
    assert 'name="telegram_bot_token"' in html
    assert 'name="email_smtp_password"' in html
    assert "secret_configured" in html
