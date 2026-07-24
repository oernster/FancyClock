"""SystemClock tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fancyclock.infrastructure.clock import SystemClock

TOLERANCE = timedelta(seconds=60)


def test_now_utc_is_aware_and_current() -> None:
    now = SystemClock().now_utc()
    assert now.tzinfo == timezone.utc
    assert abs(now - datetime.now(timezone.utc)) < TOLERANCE
