from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Protocol

from .paths import validate_watch_path
from .watcher import WatcherManager


class AppState(Protocol):
    config: dict[str, Any]
    watcher: WatcherManager | None


def activate_config(
    state: AppState,
    candidate: dict[str, Any],
    save_config_func: Callable[[dict[str, Any]], None],
    manager_factory: Callable[[dict[str, Any]], WatcherManager] = WatcherManager,
) -> str | None:
    root_path = candidate.get("watcher", {}).get("root_path", "")
    validation = validate_watch_path(root_path)
    if not validation.is_valid:
        logging.warning(
            "Rejected watcher path %r: %s (%s)",
            root_path,
            validation.error_code,
            validation.detail or "no details",
        )
        return validation.error_code

    candidate["watcher"]["root_path"] = validation.path
    new_watcher = manager_factory(candidate)
    if not new_watcher.start():
        logging.error(
            "Candidate watcher failed to start for %r: %s",
            validation.path,
            new_watcher.error or "unknown error",
        )
        new_watcher.stop()
        return "watcher_start_failed"

    try:
        save_config_func(candidate)
    except Exception:
        logging.exception("Failed to save candidate configuration for %r", validation.path)
        new_watcher.stop()
        return "config_save_failed"

    old_watcher = getattr(state, "watcher", None)
    state.config = candidate
    state.watcher = new_watcher
    if old_watcher:
        try:
            old_watcher.stop()
        except Exception:
            logging.exception("Failed to stop the previous watcher after a successful switch")
    return None
