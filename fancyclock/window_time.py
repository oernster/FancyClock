"""Clock window time/NTP behavior mixin."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from PySide6.QtCore import QDateTime


class WindowTimeMixin:
    """Adds NTP offset and clock ticking."""

    def synchronize_time(self) -> None:
        """Query NTP and compute an offset used in `_current_time()`."""
        ntp_time = self.ntp_client.get_time()
        if isinstance(ntp_time, datetime):
            local_utc_now = datetime.now(timezone.utc)
            self.time_offset = (ntp_time - local_utc_now).total_seconds()
        else:
            self.time_offset = 0

    def _current_time(self) -> QDateTime:
        """Compute current time with NTP offset and selected timezone."""
        qdt = QDateTime.currentDateTimeUtc().addSecs(int(self.time_offset))
        return qdt.toTimeZone(self.time_zone)

    def _tick_clock(self, clock_widget: Any, current_qdatetime: QDateTime) -> None:
        """Update a clock widget's time using a stable, backwards-compatible API."""
        if hasattr(clock_widget, "tick") and callable(getattr(clock_widget, "tick")):
            try:
                clock_widget.tick(current_qdatetime)
                return
            except Exception:
                pass

        if hasattr(clock_widget, "show_time") and callable(
            getattr(clock_widget, "show_time")
        ):
            try:
                if hasattr(clock_widget, "time"):
                    clock_widget.time = current_qdatetime
                clock_widget.show_time()
                return
            except Exception:
                pass

        try:
            clock_widget.time = current_qdatetime
            clock_widget.update()
        except Exception:
            try:
                clock_widget.repaint()
            except Exception:
                pass

    def update_time(self) -> None:
        """Slot called by the tick timer once per second."""
        current_qdatetime = self._current_time()
        self._tick_clock(self.analog_clock, current_qdatetime)
        self._tick_clock(self.digital_clock, current_qdatetime)
