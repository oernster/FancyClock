"""pytz implementation of the TimezoneCatalog port."""

from __future__ import annotations

from datetime import datetime

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
