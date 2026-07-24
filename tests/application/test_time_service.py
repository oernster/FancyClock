"""TimeService tests using hand-written fakes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fancyclock.application.time_service import TimeService

LOCAL_NOW = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
REFERENCE_SKEW_SECONDS = 3.0


class FakeSource:
    def utc_time(self) -> datetime:
        return LOCAL_NOW + timedelta(seconds=REFERENCE_SKEW_SECONDS)


class FakeClock:
    def now_utc(self) -> datetime:
        return LOCAL_NOW


def test_offset_starts_at_zero() -> None:
    service = TimeService(source=FakeSource(), clock=FakeClock())
    assert service.offset_seconds == 0.0


def test_synchronize_computes_offset() -> None:
    service = TimeService(source=FakeSource(), clock=FakeClock())
    assert service.synchronize() == REFERENCE_SKEW_SECONDS
    assert service.offset_seconds == REFERENCE_SKEW_SECONDS
