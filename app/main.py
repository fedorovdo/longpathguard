from __future__ import annotations

import copy
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import export_events_csv, fetch_events, init_db, set_setting, today_stats
from .i18n import normalize_language, translate
from .scanner import scan_existing
from .settings import BASE_DIR, configure_logging, load_config, save_config, validate_thresholds
from .watcher import WatcherManager, start_watcher

configure_logging()
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def _template_context(request: Request, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    config = request.app.state.config
    language = normalize_language(config.get("app", {}).get("language"))
    watcher: WatcherManager | None = getattr(request.app.state, "watcher", None)
    root_path = config.get("watcher", {}).get("root_path", "")
    context = {
        "request": request,
        "config": config,
        "language": language,
        "t": lambda key: translate(language, key),
        "watcher_running": bool(watcher and watcher.is_running),
        "watcher_error": watcher.error if watcher else None,
        "root_path_exists": os.path.isdir(root_path),
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


app = FastAPI(title="LongPathGuard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


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
async def settings_page(request: Request, saved: str | None = "", error: str | None = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "settings.html",
        _template_context(request, {"saved": bool(saved), "error": bool(error)}),
    )


@app.post("/settings")
async def update_settings(request: Request) -> RedirectResponse:
    form = await request.form()
    current = copy.deepcopy(request.app.state.config)

    try:
        current["watcher"]["root_path"] = str(form.get("root_path", "")).strip()
        current["app"]["language"] = normalize_language(str(form.get("language", "ru")))
        current["thresholds"] = {
            "max_full_path_warning": int(form.get("max_full_path_warning", 220)),
            "max_full_path_danger": int(form.get("max_full_path_danger", 240)),
            "max_full_path_critical": int(form.get("max_full_path_critical", 260)),
            "max_name_length": int(form.get("max_name_length", 120)),
        }
        excluded_paths = str(form.get("excluded_paths", "")).splitlines()
        current["watcher"]["excluded_paths"] = [path.strip() for path in excluded_paths if path.strip()]
        current.setdefault("events", {})
        current["events"]["store_ok_events"] = form.get("store_ok_events") == "on"
        current["events"]["store_modified_events"] = form.get("store_modified_events") == "on"
        current["telegram"]["enabled"] = form.get("enable_telegram_notifications") == "on"
        current["email"]["enabled"] = form.get("enable_email_notifications") == "on"
        current["scanner"]["max_scan_items"] = int(form.get("max_scan_items", 10000))
    except (TypeError, ValueError):
        return RedirectResponse("/settings?error=1", status_code=303)

    if not validate_thresholds(current["thresholds"]) or current["scanner"]["max_scan_items"] < 1:
        return RedirectResponse("/settings?error=1", status_code=303)

    save_config(current)
    set_setting("language", current["app"]["language"])
    logging.info("Settings changed")

    watcher: WatcherManager | None = getattr(request.app.state, "watcher", None)
    if watcher:
        watcher.stop()
    request.app.state.config = current
    request.app.state.watcher = start_watcher(current)
    return RedirectResponse("/settings?saved=1", status_code=303)


@app.post("/language")
async def set_language(request: Request) -> RedirectResponse:
    form = await request.form()
    language = normalize_language(str(form.get("language", "ru")))
    config = copy.deepcopy(request.app.state.config)
    config["app"]["language"] = language
    save_config(config)
    set_setting("language", language)
    request.app.state.config = config
    referer = request.headers.get("referer") or "/"
    return RedirectResponse(referer, status_code=303)


@app.get("/scan", response_class=HTMLResponse)
async def scan_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("scan.html", _template_context(request))


@app.post("/scan", response_class=HTMLResponse)
async def run_scan(request: Request) -> HTMLResponse:
    result = scan_existing(request.app.state.config)
    return templates.TemplateResponse("scan.html", _template_context(request, {"scan_result": result}))
