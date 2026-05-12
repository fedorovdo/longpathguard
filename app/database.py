from __future__ import annotations

import csv
import io
import logging
import sqlite3
from datetime import datetime
from typing import Any

from .settings import DB_PATH, ensure_project_dirs


def get_connection() -> sqlite3.Connection:
    ensure_project_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    try:
        with get_connection() as conn:
            conn.execute(
                """
                create table if not exists events (
                    id integer primary key,
                    detected_at text,
                    event_type text,
                    severity text,
                    full_path text,
                    old_full_path text nullable,
                    object_type text,
                    name text,
                    full_path_length integer,
                    name_length integer,
                    size_bytes integer nullable,
                    owner text nullable,
                    action_taken text,
                    error text nullable
                )
                """
            )
            conn.execute(
                """
                create table if not exists settings (
                    key text primary key,
                    value text
                )
                """
            )
            conn.execute(
                """
                create table if not exists app_state (
                    key text primary key,
                    value text
                )
                """
            )
            conn.execute("create index if not exists idx_events_detected_at on events(detected_at)")
            conn.execute("create index if not exists idx_events_severity on events(severity)")
            conn.execute("create index if not exists idx_events_event_type on events(event_type)")
    except sqlite3.Error:
        logging.exception("Failed to initialize SQLite database")


def insert_event(event: dict[str, Any]) -> None:
    payload = dict(event)
    payload.setdefault("detected_at", datetime.now().isoformat(timespec="seconds"))
    try:
        with get_connection() as conn:
            conn.execute(
                """
                insert into events (
                    detected_at, event_type, severity, full_path, old_full_path,
                    object_type, name, full_path_length, name_length, size_bytes,
                    owner, action_taken, error
                ) values (
                    :detected_at, :event_type, :severity, :full_path, :old_full_path,
                    :object_type, :name, :full_path_length, :name_length, :size_bytes,
                    :owner, :action_taken, :error
                )
                """,
                payload,
            )
    except sqlite3.Error:
        logging.exception("Failed to insert event into SQLite")


def _build_filters(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if filters.get("severity"):
        clauses.append("severity = ?")
        params.append(filters["severity"])
    if filters.get("event_type"):
        clauses.append("event_type = ?")
        params.append(filters["event_type"])
    if filters.get("date_from"):
        clauses.append("detected_at >= ?")
        params.append(str(filters["date_from"]) + "T00:00:00")
    if filters.get("date_to"):
        clauses.append("detected_at <= ?")
        params.append(str(filters["date_to"]) + "T23:59:59")
    if filters.get("search"):
        clauses.append("full_path like ?")
        params.append(f"%{filters['search']}%")

    where = " where " + " and ".join(clauses) if clauses else ""
    return where, params


def fetch_events(filters: dict[str, Any] | None = None, limit: int = 50) -> list[sqlite3.Row]:
    filters = filters or {}
    limit = limit if limit in {10, 50, 100, 500, 10000} else 50
    where, params = _build_filters(filters)
    try:
        with get_connection() as conn:
            return conn.execute(
                f"select * from events{where} order by detected_at desc, id desc limit ?",
                [*params, limit],
            ).fetchall()
    except sqlite3.Error:
        logging.exception("Failed to fetch events")
        return []


def today_stats() -> dict[str, int]:
    today = datetime.now().date().isoformat()
    stats = {
        "events_today": 0,
        "warning_today": 0,
        "danger_today": 0,
        "critical_today": 0,
        "long_name_today": 0,
    }
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                select severity, count(*) as count
                from events
                where detected_at like ?
                group by severity
                """,
                [today + "%"],
            ).fetchall()
    except sqlite3.Error:
        logging.exception("Failed to read dashboard stats")
        return stats

    for row in rows:
        count = int(row["count"])
        severity = row["severity"]
        stats["events_today"] += count
        if severity == "warning":
            stats["warning_today"] += count
        if severity == "danger":
            stats["danger_today"] += count
        if severity in {"critical", "critical_long_name"}:
            stats["critical_today"] += count
        if severity in {"long_name", "critical_long_name"}:
            stats["long_name_today"] += count
    return stats


def set_setting(key: str, value: str) -> None:
    try:
        with get_connection() as conn:
            conn.execute(
                "insert into settings(key, value) values(?, ?) on conflict(key) do update set value = excluded.value",
                [key, value],
            )
    except sqlite3.Error:
        logging.exception("Failed to write setting: %s", key)


def export_events_csv(filters: dict[str, Any]) -> str:
    rows = fetch_events(filters, limit=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "detected_at",
            "event_type",
            "severity",
            "object_type",
            "full_path_length",
            "name_length",
            "owner",
            "full_path",
            "old_full_path",
            "error",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["detected_at"],
                row["event_type"],
                row["severity"],
                row["object_type"],
                row["full_path_length"],
                row["name_length"],
                row["owner"],
                row["full_path"],
                row["old_full_path"],
                row["error"],
            ]
        )
    return output.getvalue()
