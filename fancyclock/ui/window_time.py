"""Clock window time/synchronisation behavior mixin."""

from __future__ import annotations

from PySide6.QtCore import QDateTime


class WindowTimeMixin:
    """Adds reference-time synchronisation and clock ticking."""

    def synchronize_time(self) -> None:
        """Recompute the clock offset from the reference time source."""
        self.time_service.synchronize()

    def _current_time(self) -> QDateTime:
        """Compute current time with the clock offset and selected timezone."""
        offset = int(self.time_service.offset_seconds)
        qdt = QDateTime.currentDateTimeUtc().addSecs(offset)
        return qdt.toTimeZone(self.time_zone)

    def update_time(self) -> None:
        """Slot called by the tick timer once per second."""
        current_qdatetime = self._current_time()
        self.analog_clock.tick(current_qdatetime)
        self.digital_clock.tick(current_qdatetime)
