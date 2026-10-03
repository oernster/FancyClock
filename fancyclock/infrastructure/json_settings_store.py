"""JSON-file implementation of the SettingsStore port."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from PySide6.QtCore import QStandardPaths

from fancyclock.infrastructure.damaged_copy import CopyFile, keep_aside

APP_NAME = "FancyClock"
SETTINGS_FILE_NAME = "settings.json"


def default_config_dir() -> Path:
    """Return the per-user configuration directory for FancyClock."""
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
    return base / APP_NAME


class JsonSettingsStore:
    """Persists settings as a JSON document with an atomic temp-file swap."""

    def __init__(
        self,
        config_dir: Path | None = None,
        copy_file: CopyFile = shutil.copyfile,
    ) -> None:
        self._config_dir = config_dir if config_dir else default_config_dir()
        self._copy_file = copy_file

    def settings_path(self) -> Path:
        """Return the settings file path, creating the directory if needed."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        return self._config_dir / SETTINGS_FILE_NAME

    def _load(self) -> dict[str, Any]:
        return self._read()[0]

    def _read(self) -> tuple[dict[str, Any], bool]:
        """Return the settings and whether an existing file was damaged."""
        path = self.settings_path()
        if not path.exists():
            return {}, False
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:  # noqa: BLE001
            # Falls back to empty settings, so the app starts on its
            # defaults rather than refusing to open. Unlike the alarms
            # document, nothing here is a promise to the user that a
            # dropped value would break. Reported as damaged so the first
            # save keeps the file aside rather than replacing it.
            return {}, True
        if not isinstance(data, dict):
            return {}, True
        return data, False

    def _save(self, data: dict[str, Any]) -> None:
        path = self.settings_path()
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        tmp.replace(path)

    def get(self, key: str, default: Any = None) -> Any:
        """Return the stored value for ``key``, else ``default``."""
        return self._load().get(key, default)

    def set(self, key: str, value: Any | None) -> None:
        """Store ``value`` under ``key``; ``None`` removes the key.

        A damaged file is copied aside first; when that copy cannot be made
        the value is not saved, so the damaged original is never replaced.
        """
        data, damaged = self._read()
        if damaged and keep_aside(self.settings_path(), self._copy_file) is None:
            return
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
        self._save(data)
