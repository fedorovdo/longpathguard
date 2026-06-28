from __future__ import annotations

from app import scanner


def make_config(root_path: str, max_items: int) -> dict:
    return {
        "watcher": {"root_path": root_path, "excluded_paths": []},
        "scanner": {"max_scan_items": max_items},
        "thresholds": {
            "max_full_path_warning": 220,
            "max_full_path_danger": 240,
            "max_full_path_critical": 260,
            "max_name_length": 3,
        },
    }


def test_scan_stops_at_configured_item_limit(tmp_path, monkeypatch) -> None:
    (tmp_path / "first-long-name.txt").write_text("1", encoding="utf-8")
    (tmp_path / "second-long-name.txt").write_text("2", encoding="utf-8")
    inserted = []
    monkeypatch.setattr(scanner, "insert_event", inserted.append)
    monkeypatch.setattr(scanner, "build_event", lambda **kwargs: {"full_path": kwargs["path"]})

    result = scanner.scan_existing(make_config(str(tmp_path), max_items=1))

    assert result.stopped_by_limit is True
    assert len(inserted) == 1


def test_subdirectory_access_error_does_not_abort_remaining_scan(tmp_path, monkeypatch) -> None:
    inserted = []

    def fake_walk(root_path, onerror):
        error = PermissionError("subdirectory denied")
        error.filename = str(tmp_path / "denied")
        onerror(error)
        yield root_path, [], ["long-name.txt"]

    monkeypatch.setattr(scanner.os, "walk", fake_walk)
    monkeypatch.setattr(scanner, "insert_event", inserted.append)
    monkeypatch.setattr(
        scanner,
        "build_event",
        lambda **kwargs: {"full_path": kwargs["path"], "error": kwargs.get("error")},
    )

    result = scanner.scan_existing(make_config(str(tmp_path), max_items=10))

    assert result.errors == 1
    assert result.detected == 1
    assert len(inserted) == 2
