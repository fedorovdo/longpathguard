from __future__ import annotations

import copy

import yaml

from app import settings


def test_default_config_has_no_server_specific_paths() -> None:
    config = copy.deepcopy(settings.DEFAULT_CONFIG)
    legacy_root = "D:" + "\\fs"
    legacy_quarantine = "D:" + "\\_LongPathQuarantine"

    assert config["watcher"]["root_path"] == ""
    assert legacy_root not in str(config)
    assert legacy_quarantine not in str(config)


def test_existing_config_keeps_legacy_root_path(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    config_path = config_dir / "config.yaml"
    config_dir.mkdir()
    legacy_root = "D:" + "\\fs"
    original = {
        "watcher": {
            "root_path": legacy_root,
            "excluded_paths": [],
        }
    }
    config_path.write_text(yaml.safe_dump(original, sort_keys=False), encoding="utf-8")
    original_text = config_path.read_text(encoding="utf-8")

    monkeypatch.setattr(settings, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(settings, "CONFIG_PATH", config_path)
    monkeypatch.setattr(settings, "DATA_DIR", data_dir)

    loaded = settings.load_config()

    assert loaded["watcher"]["root_path"] == legacy_root
    assert config_path.read_text(encoding="utf-8") == original_text
