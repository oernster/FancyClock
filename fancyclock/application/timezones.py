"""Timezone listing service for the timezone selection dialog."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

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

    def utc_offset_seconds_at(self, tz_id: str, instant_utc: datetime) -> int | None:
        """Return the UTC offset of ``tz_id`` at ``instant_utc``, else ``None``.

        Resolved through the same tzinfo the alarms schedule by, so the face
        and the alarms can never disagree about what time it is in a zone.
        ``None`` means the zone is unknown to that data.
        """
        try:
            zone = self._catalog.tzinfo_for(tz_id)
        except (KeyError, TypeError, ValueError):
            # The port raises for an unknown zone; the caller keeps its own
            # conversion rather than showing a time from no data at all.
            return None
        return int(instant_utc.astimezone(zone).utcoffset().total_seconds())
