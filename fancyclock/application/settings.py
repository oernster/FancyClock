"""Typed access to the persisted user settings."""

from __future__ import annotations

from fancyclock.application.ports import SettingsStore

SKIN_NAME_KEY = "skin_name"
TIMEZONE_ID_KEY = "timezone_id"
LOCALE_KEY = "locale"
ALARM_VOLUME_KEY = "alarm_volume"
CLOSE_TO_TRAY_KEY = "close_to_tray"

DEFAULT_ALARM_VOLUME = 0.8
MIN_VOLUME = 0.0
MAX_VOLUME = 1.0


class SettingsService:
    """Reads and writes the app's persisted settings through a store port."""

    def __init__(self, store: SettingsStore) -> None:
        self._store = store

    def skin_name(self) -> str | None:
        """Return the saved skin name, or ``None``."""
        value = self._store.get(SKIN_NAME_KEY, None)
        return value if isinstance(value, str) else None

    def set_skin_name(self, name: str | None) -> None:
        """Persist the skin name; ``None`` clears it."""
        self._store.set(SKIN_NAME_KEY, name)

    def timezone_id(self) -> str | None:
        """Return the saved timezone identifier, or ``None``."""
        value = self._store.get(TIMEZONE_ID_KEY, None)
        return value if isinstance(value, str) and value else None

    def set_timezone_id(self, tz_id: str) -> None:
        """Persist the timezone identifier."""
        self._store.set(TIMEZONE_ID_KEY, tz_id)

    def locale(self) -> str | None:
        """Return the saved locale code, or ``None``."""
        value = self._store.get(LOCALE_KEY, None)
        return value if isinstance(value, str) and value else None

    def set_locale(self, locale_code: str) -> None:
        """Persist the locale code."""
        self._store.set(LOCALE_KEY, locale_code)

    def alarm_volume(self) -> float:
        """Return the alarm volume in [0, 1], or the default."""
        value = self._store.get(ALARM_VOLUME_KEY, None)
        if isinstance(value, (int, float)) and MIN_VOLUME <= value <= MAX_VOLUME:
            return float(value)
        return DEFAULT_ALARM_VOLUME

    def set_alarm_volume(self, volume: float) -> None:
        """Persist the alarm volume, clamped to [0, 1]."""
        clamped = min(MAX_VOLUME, max(MIN_VOLUME, float(volume)))
        self._store.set(ALARM_VOLUME_KEY, clamped)

    def close_to_tray(self) -> bool:
        """Return whether closing the window hides to the tray."""
        return self._store.get(CLOSE_TO_TRAY_KEY, None) is True

    def set_close_to_tray(self, enabled: bool) -> None:
        """Persist the close-to-tray preference."""
        self._store.set(CLOSE_TO_TRAY_KEY, bool(enabled))
