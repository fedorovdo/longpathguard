from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from .settings import DATA_DIR


def normalize_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(os.path.expandvars(path)))


def is_path_excluded(path: str, config: dict[str, Any]) -> bool:
    candidate = normalize_path(path)
    excluded_paths = list(config.get("watcher", {}).get("excluded_paths", []))
    excluded_paths.append(str(DATA_DIR))

    for excluded in excluded_paths:
        if not excluded:
            continue
        excluded_norm = normalize_path(str(excluded))
        if candidate == excluded_norm or candidate.startswith(excluded_norm + os.sep):
            return True
    return False


def get_object_type(path: str, is_directory_hint: bool | None = None) -> str:
    if is_directory_hint is True:
        return "folder"
    try:
        if os.path.isdir(path):
            return "folder"
        if os.path.isfile(path):
            return "file"
    except OSError:
        logging.exception("Failed to inspect object type: %s", path)
    return "unknown"


def get_size_bytes(path: str, object_type: str) -> int | None:
    if object_type != "file":
        return None
    try:
        return os.path.getsize(path)
    except OSError:
        logging.exception("Failed to read file size: %s", path)
        return None


def get_owner(path: str) -> tuple[str, str | None]:
    if os.name == "nt":
        try:
            import win32security

            security_descriptor = win32security.GetNamedSecurityInfo(
                path,
                win32security.SE_FILE_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION,
            )
            owner_sid = security_descriptor.GetSecurityDescriptorOwner()
            name, domain, _account_type = win32security.LookupAccountSid(None, owner_sid)
            return (f"{domain}\\{name}" if domain else name), None
        except ImportError as exc:
            logging.warning("pywin32 is not installed; falling back to pathlib owner lookup")
            fallback_owner, fallback_error = _get_owner_with_pathlib(path)
            if fallback_error:
                return "", f"Owner lookup failed: pywin32 unavailable ({exc}); {fallback_error}"
            return fallback_owner, None
        except Exception as exc:
            logging.warning("Windows owner lookup failed for %s: %s", path, exc)
            return "", f"Owner lookup failed: {exc}"

    return _get_owner_with_pathlib(path)


def _get_owner_with_pathlib(path: str) -> tuple[str, str | None]:
    try:
        return Path(path).owner(), None
    except Exception as exc:
        logging.warning("Path owner lookup failed for %s: %s", path, exc)
        return "", f"Owner lookup failed: {exc}"


def _join_errors(*errors: str | None) -> str | None:
    clean_errors = [error for error in errors if error]
    return "; ".join(clean_errors) if clean_errors else None


def evaluate_severity(path: str, config: dict[str, Any]) -> str:
    thresholds = config.get("thresholds", {})
    max_warning = int(thresholds.get("max_full_path_warning", 220))
    max_danger = int(thresholds.get("max_full_path_danger", 240))
    max_critical = int(thresholds.get("max_full_path_critical", 260))
    max_name = int(thresholds.get("max_name_length", 120))

    full_path_length = len(path)
    name_length = len(os.path.basename(path.rstrip("\\/")))

    if full_path_length > max_critical and name_length > max_name:
        return "critical_long_name"
    if full_path_length > max_critical:
        return "critical"
    if name_length > max_name:
        return "long_name"
    if full_path_length > max_danger:
        return "danger"
    if full_path_length > max_warning:
        return "warning"
    return "ok"


def build_event(
    *,
    event_type: str,
    path: str,
    config: dict[str, Any],
    old_path: str | None = None,
    is_directory_hint: bool | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    clean_path = os.path.abspath(path)
    stat_error = error
    stat_result = None
    if stat_error is None:
        try:
            stat_result = os.stat(clean_path)
        except FileNotFoundError:
            stat_error = "Path does not exist"
        except PermissionError:
            stat_error = "Access denied"
        except OSError as exc:
            stat_error = str(exc)

    object_type = get_object_type(clean_path, is_directory_hint)
    name = os.path.basename(clean_path.rstrip("\\/"))
    size_bytes = stat_result.st_size if stat_result and object_type == "file" else None
    owner, owner_error = get_owner(clean_path) if stat_error is None else ("", None)

    return {
        "event_type": event_type,
        "severity": evaluate_severity(clean_path, config),
        "full_path": clean_path,
        "old_full_path": os.path.abspath(old_path) if old_path else None,
        "object_type": object_type,
        "name": name,
        "full_path_length": len(clean_path),
        "name_length": len(name),
        "size_bytes": size_bytes,
        "owner": owner,
        "action_taken": "audit",
        "error": _join_errors(stat_error, owner_error),
    }
