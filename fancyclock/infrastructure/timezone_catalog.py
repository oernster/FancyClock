"""pytz implementation of the TimezoneCatalog port."""

from __future__ import annotations

from datetime import datetime, tzinfo
from zoneinfo import ZoneInfo

import pytz


class PytzTimezoneCatalog:
    """Enumerates pytz timezones with their current UTC offsets."""

    def all_timezones(self) -> tuple[str, ...]:
        """Return every timezone identifier known to pytz."""
        return tuple(pytz.all_timezones)

    def utc_offset_seconds(self, tz_id: str) -> float:
        """Return the current UTC offset of ``tz_id`` in seconds."""
        tz = pytz.timezone(tz_id)
        local_now = datetime.now(pytz.utc).astimezone(tz)
        return local_now.utcoffset().total_seconds()

    def tzinfo_for(self, tz_id: str) -> tzinfo:
        """Return a fold-aware tzinfo for ``tz_id``; raises when unknown.

        Alarm scheduling uses PEP 495 fold semantics for its DST policy,
        which pytz timezones do not honour, so this resolves through
        ``zoneinfo`` (the identifiers are the same IANA names).
        """
        return ZoneInfo(tz_id)
