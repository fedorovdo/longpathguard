from __future__ import annotations

import copy

from fastapi.testclient import TestClient

from app.main import app
from app.metadata import (
    APP_NAME,
    APP_VERSION,
    BRAND_NAME,
    CONTACT_EMAIL_ADDRESS,
    CONTACT_EMAIL_URL,
    DEVELOPER_NAME,
    GITHUB_URL,
    WEBSITE_URL,
)
from app.settings import DEFAULT_CONFIG


def make_client(language: str = "ru") -> TestClient:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["app"]["language"] = language
    app.state.config = config
    app.state.watcher = None
    return TestClient(app)


def test_about_returns_200_and_renders_russian_content() -> None:
    response = make_client("ru").get("/about")

    assert response.status_code == 200
    assert "О программе" in response.text
    assert "помогает администраторам Windows Server" in response.text
    assert "работает только в режиме аудита" in response.text


def test_about_renders_english_content() -> None:
    response = make_client("en").get("/about")

    assert response.status_code == 200
    assert "About" in response.text
    assert "helps Windows Server administrators" in response.text
    assert "audit-only" in response.text


def test_about_shows_central_metadata_and_safe_links() -> None:
    html = make_client("en").get("/about").text

    for value in (APP_NAME, APP_VERSION, BRAND_NAME, DEVELOPER_NAME):
        assert value in html
    assert f'href="{WEBSITE_URL}"' in html
    assert f'href="{GITHUB_URL}"' in html
    assert f'href="{CONTACT_EMAIL_URL}"' in html
    assert CONTACT_EMAIL_ADDRESS in html
    assert 'target="_blank" rel="noopener noreferrer"' in html


def test_about_has_brand_assets_favicon_and_active_navigation() -> None:
    html = make_client("en").get("/about").text

    assert "/static/brand/simply-admin-logo-dark.png" in html
    assert "/static/brand/simply-admin-mark-light.png" in html
    assert "/static/brand/simply-admin-mark-dark.png" in html
    assert 'rel="icon" type="image/png"' in html
    assert 'href="/about" class="active"' in html


def test_about_never_renders_notification_secrets() -> None:
    telegram_secret = "about-must-not-render-telegram-token"
    email_secret = "about-must-not-render-smtp-password"
    client = make_client("en")
    app.state.config["telegram"]["bot_token"] = telegram_secret
    app.state.config["email"]["smtp_password"] = email_secret

    html = client.get("/about").text

    assert telegram_secret not in html
    assert email_secret not in html
