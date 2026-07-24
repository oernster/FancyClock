"""Typed access to the persisted user settings."""

from __future__ import annotations

from fancyclock.application.ports import SettingsStore

SKIN_NAME_KEY = "skin_name"
TIMEZONE_ID_KEY = "timezone_id"
LOCALE_KEY = "locale"


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
