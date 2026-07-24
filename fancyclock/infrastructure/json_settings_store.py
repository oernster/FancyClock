"""JSON-file implementation of the SettingsStore port."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QStandardPaths

APP_NAME = "FancyClock"
SETTINGS_FILE_NAME = "settings.json"


def default_config_dir() -> Path:
    """Return the per-user configuration directory for FancyClock."""
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
    return base / APP_NAME


class JsonSettingsStore:
    """Persists settings as a JSON document with an atomic temp-file swap."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir if config_dir else default_config_dir()

    def settings_path(self) -> Path:
        """Return the settings file path, creating the directory if needed."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        return self._config_dir / SETTINGS_FILE_NAME

    def _load(self) -> dict[str, Any]:
        path = self.settings_path()
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        path = self.settings_path()
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        tmp.replace(path)

    def get(self, key: str, default: Any = None) -> Any:
        """Return the stored value for ``key``, or ``default``."""
        return self._load().get(key, default)

    def set(self, key: str, value: Any | None) -> None:
        """Store ``value`` under ``key``; ``None`` removes the key."""
        data = self._load()
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
        self._save(data)
