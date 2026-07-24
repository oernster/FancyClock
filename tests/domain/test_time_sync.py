"""Domain clock-offset tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fancyclock.domain.time_sync import clock_offset_seconds


def test_clock_offset_seconds() -> None:
    local = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    reference = local + timedelta(seconds=2.5)
    assert clock_offset_seconds(reference, local) == 2.5
    assert clock_offset_seconds(local, reference) == -2.5
