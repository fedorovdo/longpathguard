from __future__ import annotations

import copy
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import export_events_csv, fetch_events, init_db, set_setting, today_stats
from . import metadata
from .i18n import normalize_language, translate
from .notification_settings import NOTIFICATION_SEVERITIES, update_notification_config
from .notifier import NOTIFICATION_STATUSES, send_email, send_telegram
from .paths import normalize_windows_path, validate_watch_path
from .runtime import activate_config
from .scanner import scan_existing
from .settings import BASE_DIR, configure_logging, load_config, save_config, validate_thresholds
from .watcher import WatcherManager, start_watcher

configure_logging()
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

UI_ERROR_CODES = {
    "invalid_settings",
    "path_required",
    "path_not_absolute",
    "path_not_found",
    "path_not_directory",
    "path_access_denied",
    "watcher_start_failed",
    "config_save_failed",
    "notification_severity_invalid",
    "telegram_token_required",
    "telegram_chat_id_required",
    "email_smtp_host_required",
    "email_from_addr_required",
    "email_to_addr_required",
    "email_smtp_port_invalid",
}

UI_NOTICE_CODES = {
    f"{provider}_test_{status}"
    for provider in ("telegram", "email")
    for status in NOTIFICATION_STATUSES
}


def _template_context(request: Request, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    config = request.app.state.config
    language = normalize_language(config.get("app", {}).get("language"))
    watcher: WatcherManager | None = getattr(request.app.state, "watcher", None)
    root_path = config.get("watcher", {}).get("root_path", "")
    path_status = validate_watch_path(root_path)
    telegram = config.get("telegram", {})
    email = config.get("email", {})
    try:
        email_port = int(email.get("smtp_port", 587))
        email_port_valid = 1 <= email_port <= 65535
    except (TypeError, ValueError):
        email_port_valid = False
    context = {
        "request": request,
        "config": config,
        "meta": metadata,
        "language": language,
        "t": lambda key: translate(language, key),
        "watcher_running": bool(watcher and watcher.is_running),
        "watcher_error_code": watcher.error_code if watcher else None,
        "root_path_available": path_status.is_valid,
        "root_path_error_code": path_status.error_code,
        "notification_severity_values": NOTIFICATION_SEVERITIES,
        "telegram_secret_configured": bool(telegram.get("bot_token")),
        "telegram_test_ready": bool(
            telegram.get("enabled") and telegram.get("bot_token") and telegram.get("chat_id")
        ),
        "email_secret_configured": bool(email.get("smtp_password")),
        "email_test_ready": bool(
            email.get("enabled")
            and email.get("smtp_host")
            and email.get("from_addr")
            and email.get("to_addr")
            and email_port_valid
        ),
    }
    if extra:
        context.update(extra)
    return context


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("LongPathGuard starting")
    init_db()
    config = load_config()
    app.state.config = config
    app.state.watcher = start_watcher(config)
    try:
        yield
    finally:
        watcher: WatcherManager | None = getattr(app.state, "watcher", None)
        if watcher:
            watcher.stop()
        logging.info("LongPathGuard stopped")


app = FastAPI(title=metadata.APP_NAME, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "about.html", _template_context(request))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    stats = today_stats()
    latest_events = fetch_events(limit=10)
    return templates.TemplateResponse(
        "dashboard.html",
        _template_context(request, {"stats": stats, "latest_events": latest_events}),
    )


def _filters(
    severity: str | None,
    event_type: str | None,
    date_from: str | None,
    date_to: str | None,
    search: str | None,
) -> dict[str, Any]:
    return {
        "severity": severity or "",
        "event_type": event_type or "",
        "date_from": date_from or "",
        "date_to": date_to or "",
        "search": search or "",
    }


@app.get("/events", response_class=HTMLResponse)
async def events(
    request: Request,
    severity: str | None = "",
    event_type: str | None = "",
    date_from: str | None = "",
    date_to: str | None = "",
    search: str | None = "",
    limit: int = Query(default=50),
) -> HTMLResponse:
    filters = _filters(severity, event_type, date_from, date_to, search)
    selected_limit = limit if limit in {50, 100, 500} else 50
    rows = fetch_events(filters, selected_limit)
    return templates.TemplateResponse(
        "events.html",
        _template_context(
            request,
            {
                "events": rows,
                "filters": filters,
                "limit": selected_limit,
                "severity_values": ["warning", "danger", "critical", "long_name", "critical_long_name", "ok"],
                "event_type_values": ["created", "renamed", "modified", "scan_detected"],
            },
        ),
    )


@app.get("/events/export.csv")
async def export_csv(
    severity: str | None = "",
    event_type: str | None = "",
    date_from: str | None = "",
    date_to: str | None = "",
    search: str | None = "",
) -> Response:
    filters = _filters(severity, event_type, date_from, date_to, search)
    content = export_events_csv(filters)
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=longpathguard-events.csv"},
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    saved: str | None = "",
    error: str | None = "",
    notice: str | None = "",
) -> HTMLResponse:
    error_code = error if error in UI_ERROR_CODES else ("invalid_settings" if error else None)
    notice_code = notice if notice in UI_NOTICE_CODES else None
    return templates.TemplateResponse(
        "settings.html",
        _template_context(
            request,
            {
                "saved": bool(saved),
                "error_code": error_code,
                "notice_code": notice_code,
                "notice_success": bool(notice_code and notice_code.endswith("_success")),
            },
        ),
    )


@app.post("/settings")
async def update_settings(request: Request) -> RedirectResponse:
    form = await request.form()
    current = copy.deepcopy(request.app.state.config)

    try:
        current["watcher"]["root_path"] = normalize_windows_path(str(form.get("root_path", "")))
        current["app"]["language"] = normalize_language(str(form.get("language", "ru")).strip())
        current["thresholds"] = {
            "max_full_path_warning": int(form.get("max_full_path_warning", 220)),
            "max_full_path_danger": int(form.get("max_full_path_danger", 240)),
            "max_full_path_critical": int(form.get("max_full_path_critical", 260)),
            "max_name_length": int(form.get("max_name_length", 120)),
        }
        excluded_paths = str(form.get("excluded_paths", "")).splitlines()
        current["watcher"]["excluded_paths"] = [
            normalize_windows_path(path) for path in excluded_paths if path.strip()
        ]
        current.setdefault("events", {})
        current["events"]["store_ok_events"] = form.get("store_ok_events") == "on"
        current["events"]["store_modified_events"] = form.get("store_modified_events") == "on"
        current["scanner"]["max_scan_items"] = int(form.get("max_scan_items", 10000))
    except (TypeError, ValueError):
        return RedirectResponse("/settings?error=1", status_code=303)

    if not validate_thresholds(current["thresholds"]) or current["scanner"]["max_scan_items"] < 1:
        return RedirectResponse("/settings?error=1", status_code=303)

    notification_error = update_notification_config(current, form)
    if notification_error:
        return RedirectResponse(f"/settings?error={notification_error}", status_code=303)

    error_code = activate_config(request.app.state, current, save_config)
    if error_code:
        return RedirectResponse(f"/settings?error={error_code}", status_code=303)

    set_setting("language", current["app"]["language"])
    logging.info("Settings changed")
    return RedirectResponse("/settings?saved=1", status_code=303)


@app.post("/settings/test/telegram")
async def test_telegram_notification(request: Request) -> RedirectResponse:
    config = request.app.state.config
    language = normalize_language(config.get("app", {}).get("language"))
    result = send_telegram(translate(language, "telegram_test_body"), config)
    return RedirectResponse(f"/settings?notice=telegram_test_{result.status}", status_code=303)


@app.post("/settings/test/email")
async def test_email_notification(request: Request) -> RedirectResponse:
    config = request.app.state.config
    language = normalize_language(config.get("app", {}).get("language"))
    result = send_email(
        translate(language, "email_test_subject"),
        translate(language, "email_test_body"),
        config,
    )
    return RedirectResponse(f"/settings?notice=email_test_{result.status}", status_code=303)


@app.post("/language")
async def set_language(request: Request) -> RedirectResponse:
    form = await request.form()
    language = normalize_language(str(form.get("language", "ru")))
    config = copy.deepcopy(request.app.state.config)
    config["app"]["language"] = language
    referer = request.headers.get("referer") or "/"
    try:
        save_config(config)
    except Exception:
        logging.exception("Failed to save language setting")
        return RedirectResponse(referer, status_code=303)
    set_setting("language", language)
    request.app.state.config = config
    return RedirectResponse(referer, status_code=303)


@app.get("/scan", response_class=HTMLResponse)
async def scan_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("scan.html", _template_context(request))


@app.post("/scan", response_class=HTMLResponse)
async def run_scan(request: Request) -> HTMLResponse:
    config = request.app.state.config
    path_status = validate_watch_path(config.get("watcher", {}).get("root_path", ""))
    if not path_status.is_valid:
        return templates.TemplateResponse(
            "scan.html",
            _template_context(request, {"scan_error_code": path_status.error_code}),
        )

    result = scan_existing(config)
    return templates.TemplateResponse(
        "scan.html",
        _template_context(
            request,
            {"scan_result": result, "scan_error_code": result.error_code},
        ),
    )
