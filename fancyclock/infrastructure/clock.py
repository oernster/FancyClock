"""System wall-clock implementation of the Clock port."""

from __future__ import annotations

from datetime import datetime, timezone


class SystemClock:
    """Reads the local system clock."""

    def now_utc(self) -> datetime:
        """Return the current system time as an aware UTC datetime."""
        return datetime.now(timezone.utc)
