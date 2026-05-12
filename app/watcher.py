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
from .security import build_event, is_path_excluded


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

        insert_event(event)
        notify_event(event)


class WatcherManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.observer: Observer | None = None
        self.error: str | None = None

    @property
    def is_running(self) -> bool:
        return bool(self.observer and self.observer.is_alive())

    def start(self) -> None:
        root_path = self.config.get("watcher", {}).get("root_path", "")
        if not root_path or not os.path.isdir(root_path):
            self.error = f"Root path does not exist: {root_path}"
            logging.warning(self.error)
            return

        try:
            handler = LongPathEventHandler(self.config)
            self.observer = Observer()
            self.observer.schedule(handler, root_path, recursive=True)
            self.observer.start()
            logging.info("Watcher started for %s", root_path)
        except Exception as exc:
            self.error = str(exc)
            logging.exception("Failed to start watcher")

    def stop(self) -> None:
        if not self.observer:
            return
        self.observer.stop()
        self.observer.join(timeout=10)
        logging.info("Watcher stopped")


def start_watcher(config: dict[str, Any]) -> WatcherManager:
    manager = WatcherManager(config)
    manager.start()
    return manager
