"""Interfaces (ports) implemented by the infrastructure layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class Clock(Protocol):
    """Reads the local wall clock."""

    def now_utc(self) -> datetime:
        """Return the current local system time as an aware UTC datetime."""
        ...


class TimeSource(Protocol):
    """Provides an authoritative reference time (for example NTP)."""

    def utc_time(self) -> datetime:
        """Return the best available reference time as an aware UTC datetime."""
        ...


class SettingsStore(Protocol):
    """Persists user settings as key-value pairs."""

    def get(self, key: str, default: Any = None) -> Any:
        """Return the stored value for ``key``, or ``default``."""
        ...

    def set(self, key: str, value: Any | None) -> None:
        """Store ``value`` under ``key``; ``None`` removes the key."""
        ...


class TranslationsRepository(Protocol):
    """Loads translation dictionaries by locale code."""

    def load(self, locale_code: str) -> dict[str, Any] | None:
        """Return the translations for ``locale_code``, or ``None``."""
        ...


class TimezoneLocaleMap(Protocol):
    """Maps timezone identifiers to locale codes."""

    def locale_for(self, tz_id: str | None) -> str | None:
        """Return the locale for ``tz_id`` (``None`` means the system zone)."""
        ...


class SystemLocaleProbe(Protocol):
    """Reads raw locale hints from the host system."""

    def candidates(self) -> tuple[str, ...]:
        """Return raw locale strings in preference order."""
        ...


class TimezoneCatalog(Protocol):
    """Enumerates timezones and their current UTC offsets."""

    def all_timezones(self) -> tuple[str, ...]:
        """Return every known timezone identifier."""
        ...

    def utc_offset_seconds(self, tz_id: str) -> float:
        """Return the current UTC offset of ``tz_id`` in seconds."""
        ...


class MediaLibrary(Protocol):
    """Enumerates the bundled video skin files."""

    def skin_files(self) -> tuple[str, ...]:
        """Return absolute paths of the available skin files, sorted."""
        ...
