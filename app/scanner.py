from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from .database import insert_event
from .security import build_event, evaluate_severity, is_path_excluded


@dataclass
class ScanResult:
    scanned: int = 0
    detected: int = 0
    errors: int = 0
    stopped_by_limit: bool = False


def _record_error(path: str, config: dict[str, Any], error: str) -> None:
    event = build_event(
        event_type="scan_detected",
        path=path,
        config=config,
        error=error,
    )
    insert_event(event)


def scan_existing(config: dict[str, Any]) -> ScanResult:
    result = ScanResult()
    root_path = config.get("watcher", {}).get("root_path", "")
    max_items = int(config.get("scanner", {}).get("max_scan_items", 10000))

    if not os.path.isdir(root_path):
        result.errors += 1
        _record_error(root_path or ".", config, "Root path does not exist")
        return result

    def onerror(error: OSError) -> None:
        result.errors += 1
        logging.exception("Scan access error: %s", error)
        _record_error(getattr(error, "filename", root_path) or root_path, config, str(error))

    for dirpath, dirnames, filenames in os.walk(root_path, onerror=onerror):
        if is_path_excluded(dirpath, config):
            dirnames[:] = []
            continue

        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not is_path_excluded(os.path.join(dirpath, dirname), config)
        ]

        for name, is_dir in [(dirname, True) for dirname in dirnames] + [(filename, False) for filename in filenames]:
            path = os.path.join(dirpath, name)
            if is_path_excluded(path, config):
                continue
            result.scanned += 1
            if result.scanned > max_items:
                result.stopped_by_limit = True
                return result

            try:
                severity = evaluate_severity(os.path.abspath(path), config)
                if severity == "ok":
                    continue
                event = build_event(
                    event_type="scan_detected",
                    path=path,
                    config=config,
                    is_directory_hint=is_dir,
                )
                insert_event(event)
                result.detected += 1
            except Exception as exc:
                result.errors += 1
                logging.exception("Scan failed for %s", path)
                _record_error(path, config, str(exc))

    return result
