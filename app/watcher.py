from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileMovedEvent
from watchdog.observers import Observer

from .database import insert_event
from .notifier import notify_event
from .paths import validate_watch_path
from .security import build_event, is_path_excluded


def should_store_event(event: dict[str, Any], config: dict[str, Any]) -> bool:
    if event.get("error"):
        return True

    events_config = config.get("events", {})
    severity = event.get("severity", "ok")
    event_type = event.get("event_type", "")

    if event_type == "modified" and not events_config.get("store_modified_events", False):
        return severity != "ok"

    if severity == "ok" and not events_config.get("store_ok_events", False):
        return False

    return True


class LongPathEventHandler(FileSystemEventHandler):
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._modified_seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle_event("created", event.src_path, event.is_directory)

    def on_moved(self, event: FileMovedEvent) -> None:
        self._handle_event("renamed", event.dest_path, event.is_directory, old_path=event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        debounce = float(self.config.get("watcher", {}).get("modified_debounce_seconds", 2))
        now = time.monotonic()
        key = os.path.normcase(event.src_path)
        with self._lock:
            last = self._modified_seen.get(key, 0)
            if now - last < debounce:
                return
            self._modified_seen[key] = now
        self._handle_event("modified", event.src_path, event.is_directory)

    def _handle_event(
        self,
        event_type: str,
        path: str,
        is_directory: bool | None,
        old_path: str | None = None,
    ) -> None:
        if is_path_excluded(path, self.config):
            return
        try:
            event = build_event(
                event_type=event_type,
                path=path,
                old_path=old_path,
                is_directory_hint=is_directory,
                config=self.config,
            )
        except Exception as exc:
            logging.exception("Failed to process filesystem event: %s", path)
            event = build_event(
                event_type=event_type,
                path=path,
                old_path=old_path,
                is_directory_hint=is_directory,
                config=self.config,
                error=str(exc),
            )

        if should_store_event(event, self.config):
            insert_event(event)
            notify_event(event)


class WatcherManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.observer: Observer | None = None
        self.error: str | None = None
        self.error_code: str | None = None

    @property
    def is_running(self) -> bool:
        return bool(self.observer and self.observer.is_alive())

    def start(self) -> bool:
        root_path = self.config.get("watcher", {}).get("root_path", "")
        validation = validate_watch_path(root_path)
        if not validation.is_valid:
            self.error_code = validation.error_code
            self.error = validation.detail
            if validation.error_code == "path_required":
                logging.info("Watcher is not started because root_path is not configured")
            else:
                logging.warning(
                    "Watcher path %r is unavailable: %s (%s)",
                    root_path,
                    validation.error_code,
                    validation.detail or "no details",
                )
            return False

        try:
            handler = LongPathEventHandler(self.config)
            self.observer = Observer()
            self.observer.schedule(handler, validation.path, recursive=True)
            self.observer.start()
            if not self.observer.is_alive():
                raise RuntimeError("Observer stopped immediately after start")
            self.error = None
            self.error_code = None
            logging.info("Watcher started for %s", validation.path)
            return True
        except Exception as exc:
            self.error_code = "watcher_start_failed"
            self.error = str(exc)
            logging.exception("Failed to start watcher")
            self.stop()
            return False

    def stop(self) -> None:
        observer = self.observer
        self.observer = None
        if not observer:
            return
        try:
            observer.stop()
            if observer.is_alive():
                observer.join(timeout=10)
            logging.info("Watcher stopped")
        except Exception:
            logging.exception("Failed to stop watcher cleanly")


def start_watcher(config: dict[str, Any]) -> WatcherManager:
    manager = WatcherManager(config)
    manager.start()
    return manager
