from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
DATA_DIR = BASE_DIR / "data"
LOG_PATH = DATA_DIR / "longpathguard.log"
DB_PATH = DATA_DIR / "longpathguard.db"

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {
        "language": "ru",
        "audit_mode": True,
        "host": "127.0.0.1",
        "port": 8787,
    },
    "events": {
        "store_ok_events": False,
        "store_modified_events": False,
    },
    "watcher": {
        "root_path": "",
        "excluded_paths": [
            str(DATA_DIR),
        ],
        "modified_debounce_seconds": 2,
    },
    "thresholds": {
        "max_full_path_warning": 220,
        "max_full_path_danger": 240,
        "max_full_path_critical": 260,
        "max_name_length": 120,
    },
    "scanner": {
        "max_scan_items": 10000,
    },
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": "",
        "min_severity": "critical",
    },
    "email": {
        "enabled": False,
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "from_addr": "",
        "to_addr": "",
        "use_tls": True,
        "min_severity": "critical",
    },
}


def ensure_project_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _deep_merge(defaults: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(defaults)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict[str, Any]:
    ensure_project_dirs()
    if not CONFIG_PATH.exists():
        save_config(copy.deepcopy(DEFAULT_CONFIG))
        return copy.deepcopy(DEFAULT_CONFIG)

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file) or {}
    except Exception:
        logging.exception("Failed to read config.yaml; using defaults")
        loaded = {}

    if not isinstance(loaded, dict):
        loaded = {}
    return _deep_merge(DEFAULT_CONFIG, loaded)


def save_config(config: dict[str, Any]) -> None:
    ensure_project_dirs()
    temporary_path = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)
    temporary_path.replace(CONFIG_PATH)


def validate_thresholds(thresholds: dict[str, Any]) -> bool:
    keys = [
        "max_full_path_warning",
        "max_full_path_danger",
        "max_full_path_critical",
        "max_name_length",
    ]
    try:
        values = {key: int(thresholds[key]) for key in keys}
    except (KeyError, TypeError, ValueError):
        return False

    return (
        1 <= values["max_name_length"]
        and 1 <= values["max_full_path_warning"]
        < values["max_full_path_danger"]
        < values["max_full_path_critical"]
    )


def configure_logging() -> None:
    ensure_project_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
