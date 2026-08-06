"""Interfaces (ports) implemented by the infrastructure layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Any, Protocol

from fancyclock.domain.alarms import Alarm, AlarmsState


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
        """Return the stored value for ``key``, else ``default``."""
        ...

    def set(self, key: str, value: Any | None) -> None:
        """Store ``value`` under ``key``; ``None`` removes the key."""
        ...


class TranslationsRepository(Protocol):
    """Loads translation dictionaries by locale code."""

    def load(self, locale_code: str) -> dict[str, Any] | None:
        """Return the translations for ``locale_code``, else ``None``."""
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

    def tzinfo_for(self, tz_id: str) -> tzinfo:
        """Return a fold-aware tzinfo for ``tz_id``; raises when unknown."""
        ...


@dataclass(frozen=True, slots=True)
class AlarmLoad:
    """The persisted state, together with what the load could not read.

    A tolerant load is right for an alarm document: one unreadable entry must
    never stop the application starting. Staying silent about it is not, since
    a skipped entry is an alarm that will not ring; not ringing is the
    worst thing an alarm clock can do. The counts travel back beside the state
    so the caller can say so once, rather than the store deciding on its own
    that nobody needs to know.
    """

    state: AlarmsState
    skipped_alarms: int = 0
    skipped_snoozes: int = 0

    @property
    def lost_entries(self) -> int:
        """Return how many stored entries could not be read."""
        return self.skipped_alarms + self.skipped_snoozes


class AlarmStore(Protocol):
    """Persists the whole alarm document."""

    def load(self) -> AlarmLoad:
        """Return the persisted state plus what could not be read."""
        ...

    def save(self, state: AlarmsState) -> None:
        """Persist ``state`` atomically."""
        ...


class AlarmPorter(Protocol):
    """Imports and exports alarms as a versioned JSON document."""

    def export_alarms(self, path: Path, alarms: tuple[Alarm, ...]) -> None:
        """Write ``alarms`` to ``path``."""
        ...

    def import_alarms(self, path: Path) -> tuple[Alarm, ...]:
        """Read alarms from ``path``; raises ``AlarmImportError`` on bad data."""
        ...


class AutostartManager(Protocol):
    """Controls launching the app when the user signs in."""

    def is_supported(self) -> bool:
        """Return whether autostart can be managed on this platform."""
        ...

    def is_enabled(self) -> bool:
        """Return whether autostart is currently enabled."""
        ...

    def enable(self) -> None:
        """Enable start-on-sign-in."""
        ...

    def disable(self) -> None:
        """Disable start-on-sign-in."""
        ...


class MediaLibrary(Protocol):
    """Enumerates the bundled video skin files."""

    def skin_files(self) -> tuple[str, ...]:
        """Return absolute paths of the available skin files, sorted."""
        ...
