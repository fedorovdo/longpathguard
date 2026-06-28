from __future__ import annotations

import ntpath
import os
import stat
from dataclasses import dataclass


@dataclass(frozen=True)
class PathValidationResult:
    path: str
    error_code: str | None = None
    detail: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.error_code is None


def normalize_windows_path(value: str | None) -> str:
    path = str(value or "").strip()
    if len(path) >= 2 and path[0] == path[-1] and path[0] in {'"', "'"}:
        path = path[1:-1].strip()
    if not path:
        return ""
    return ntpath.normpath(os.path.expandvars(path))


def validate_watch_path(value: str | None) -> PathValidationResult:
    path = normalize_windows_path(value)
    if not path:
        return PathValidationResult(path=path, error_code="path_required")
    if not ntpath.isabs(path):
        return PathValidationResult(path=path, error_code="path_not_absolute")

    try:
        path_stat = os.stat(path)
    except FileNotFoundError as exc:
        return PathValidationResult(path=path, error_code="path_not_found", detail=str(exc))
    except PermissionError as exc:
        return PathValidationResult(path=path, error_code="path_access_denied", detail=str(exc))
    except OSError as exc:
        return PathValidationResult(path=path, error_code="path_not_found", detail=str(exc))

    if not stat.S_ISDIR(path_stat.st_mode):
        return PathValidationResult(path=path, error_code="path_not_directory")

    try:
        with os.scandir(path) as entries:
            next(entries, None)
    except (PermissionError, OSError) as exc:
        return PathValidationResult(path=path, error_code="path_access_denied", detail=str(exc))

    return PathValidationResult(path=path)
