from __future__ import annotations

import ntpath

from app import paths


def test_normalizes_quoted_local_path_with_trailing_slash() -> None:
    value = '  "C:\\Folder Name\\"  '

    assert paths.normalize_windows_path(value) == ntpath.normpath(r"C:\Folder Name")


def test_normalizes_unc_path_without_damaging_prefix() -> None:
    value = '"\\\\fileserver\\share\\Folder Name\\"'

    normalized = paths.normalize_windows_path(value)

    assert normalized == ntpath.normpath(r"\\fileserver\share\Folder Name")
    assert normalized.startswith(r"\\")


def test_expands_windows_environment_variable(monkeypatch) -> None:
    monkeypatch.setenv("LPG_TEST_ROOT", r"C:\LongPathGuard")

    assert paths.normalize_windows_path(r"%LPG_TEST_ROOT%\Data") == ntpath.normpath(
        r"C:\LongPathGuard\Data"
    )


def test_rejects_relative_path() -> None:
    result = paths.validate_watch_path(r"relative\folder")

    assert result.error_code == "path_not_absolute"


def test_rejects_missing_folder(tmp_path) -> None:
    result = paths.validate_watch_path(str(tmp_path / "missing"))

    assert result.error_code == "path_not_found"


def test_rejects_file_instead_of_folder(tmp_path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("test", encoding="utf-8")

    result = paths.validate_watch_path(str(file_path))

    assert result.error_code == "path_not_directory"


def test_detects_read_access_error(tmp_path, monkeypatch) -> None:
    def deny_access(_path):
        raise PermissionError("denied")

    monkeypatch.setattr(paths.os, "scandir", deny_access)

    result = paths.validate_watch_path(str(tmp_path))

    assert result.error_code == "path_access_denied"
