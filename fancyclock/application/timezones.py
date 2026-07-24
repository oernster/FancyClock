"""Timezone listing service for the timezone selection dialog."""

from __future__ import annotations

from dataclasses import dataclass

from fancyclock.application.ports import TimezoneCatalog
from fancyclock.domain.timezones import format_timezone_entry


@dataclass(frozen=True, slots=True)
class TimezoneEntry:
    """One selectable timezone with its display text."""

    display: str
    tz_id: str


class TimezoneService:
    """Builds the sorted timezone listing shown in the selection dialog."""

    def __init__(self, catalog: TimezoneCatalog) -> None:
        self._catalog = catalog

    def entries(self) -> tuple[TimezoneEntry, ...]:
        """Return every timezone with display text, sorted by display text."""
        items = [
            TimezoneEntry(
                display=format_timezone_entry(
                    tz_id, self._catalog.utc_offset_seconds(tz_id)
                ),
                tz_id=tz_id,
            )
            for tz_id in self._catalog.all_timezones()
        ]
        items.sort(key=lambda entry: entry.display)
        return tuple(items)
