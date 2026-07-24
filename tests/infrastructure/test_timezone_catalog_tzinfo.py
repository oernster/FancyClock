"""tzinfo_for tests for the pytz-backed timezone catalog."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fancyclock.infrastructure.timezone_catalog import PytzTimezoneCatalog


def test_tzinfo_for_returns_a_fold_aware_zone() -> None:
    tz = PytzTimezoneCatalog().tzinfo_for("Europe/London")
    summer = datetime(2026, 7, 1, 12, 0, tzinfo=tz)
    assert summer.utcoffset().total_seconds() == 3600
    assert summer.astimezone(timezone.utc).hour == 11


def test_tzinfo_for_unknown_zone_raises() -> None:
    with pytest.raises(Exception):
        PytzTimezoneCatalog().tzinfo_for("Nowhere/Bad")
