from __future__ import annotations

from app import scanner


def make_config(root_path: str, excluded_paths: list[str] | None = None) -> dict:
    return {
        "watcher": {
            "root_path": root_path,
            "excluded_paths": excluded_paths or [],
        },
        "scanner": {"max_scan_items": 100},
        "thresholds": {
            "max_full_path_warning": 220,
            "max_full_path_danger": 240,
            "max_full_path_critical": 260,
            "max_name_length": 3,
        },
    }


def test_scan_uses_root_path_from_passed_current_config(tmp_path, monkeypatch) -> None:
    first = tmp_path / "first"
    current = tmp_path / "current"
    first.mkdir()
    current.mkdir()
    (current / "long-name.txt").write_text("data", encoding="utf-8")
    inserted = []

    monkeypatch.setattr(scanner, "insert_event", inserted.append)
    monkeypatch.setattr(
        scanner,
        "build_event",
        lambda **kwargs: {"full_path": kwargs["path"], "event_type": "scan_detected"},
    )

    result = scanner.scan_existing(make_config(str(current)))

    assert result.detected == 1
    assert len(inserted) == 1
    assert inserted[0]["full_path"].startswith(str(current))
    assert not inserted[0]["full_path"].startswith(str(first))


def test_scan_keeps_exclusions_and_limit(tmp_path, monkeypatch) -> None:
    included = tmp_path / "included"
    excluded = tmp_path / "excluded"
    included.mkdir()
    excluded.mkdir()
    (included / "long-name.txt").write_text("data", encoding="utf-8")
    (excluded / "other-long-name.txt").write_text("data", encoding="utf-8")
    inserted = []

    monkeypatch.setattr(scanner, "insert_event", inserted.append)
    monkeypatch.setattr(
        scanner,
        "build_event",
        lambda **kwargs: {"full_path": kwargs["path"], "event_type": "scan_detected"},
    )
    config = make_config(str(tmp_path), [str(excluded)])
    config["scanner"]["max_scan_items"] = 10

    result = scanner.scan_existing(config)

    assert result.stopped_by_limit is False
    assert len(inserted) == 2
    assert all(str(excluded) not in event["full_path"] for event in inserted)


def test_unconfigured_scan_does_not_write_false_event(monkeypatch) -> None:
    inserted = []
    monkeypatch.setattr(scanner, "insert_event", inserted.append)

    result = scanner.scan_existing(make_config(""))

    assert result.error_code == "path_required"
    assert inserted == []
