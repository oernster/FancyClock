# settings_store.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from PySide6.QtCore import QStandardPaths

APP_NAME = "FancyClock"
SETTINGS_FILE_NAME = "settings.json"


def app_config_dir() -> Path:
    """
    Return the per-user configuration directory for FancyClock,
    creating it if needed.
    """
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
    cfg = base / APP_NAME
    cfg.mkdir(parents=True, exist_ok=True)
    return cfg


def settings_path() -> Path:
    return app_config_dir() / SETTINGS_FILE_NAME


def load_settings() -> Dict[str, Any]:
    """Load settings.json, returning {} if missing or invalid."""
    path = settings_path()
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        # Broken JSON? Just ignore and start fresh.
        return {}


def save_settings(data: Dict[str, Any]) -> None:
    """Write JSON with a simple temp-file swap for safety."""
    path = settings_path()
    tmp = path.with_suffix(".tmp")

    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)

    tmp.replace(path)


def get_setting(key: str, default: Any = None) -> Any:
    return load_settings().get(key, default)


def set_setting(key: str, value: Any | None) -> None:
    data = load_settings()
    if value is None:
        data.pop(key, None)
    else:
        data[key] = value
    save_settings(data)
