"""Reference-time synchronisation service."""

from __future__ import annotations

from fancyclock.application.ports import Clock, TimeSource
from fancyclock.domain.time_sync import clock_offset_seconds


class TimeService:
    """Tracks the offset between the local clock and a reference source."""

    def __init__(self, source: TimeSource, clock: Clock) -> None:
        self._source = source
        self._clock = clock
        self._offset_seconds = 0.0

    @property
    def offset_seconds(self) -> float:
        """Return the last computed clock offset in seconds."""
        return self._offset_seconds

    def synchronize(self) -> float:
        """Query the reference source and recompute the clock offset."""
        reference = self._source.utc_time()
        local = self._clock.now_utc()
        self._offset_seconds = clock_offset_seconds(reference, local)
        return self._offset_seconds
