"""PytzTimezoneCatalog tests against the real pytz database."""

from __future__ import annotations

from fancyclock.domain.timezones import SECONDS_PER_HOUR
from fancyclock.infrastructure.timezone_catalog import PytzTimezoneCatalog


def test_all_timezones_contains_well_known_zones() -> None:
    catalog = PytzTimezoneCatalog()
    zones = catalog.all_timezones()
    assert "Europe/London" in zones
    assert "UTC" in zones


def test_utc_offset_of_utc_is_zero() -> None:
    catalog = PytzTimezoneCatalog()
    assert catalog.utc_offset_seconds("UTC") == 0.0


def test_utc_offset_of_london_is_gmt_or_bst() -> None:
    catalog = PytzTimezoneCatalog()
    assert catalog.utc_offset_seconds("Europe/London") in (
        0.0,
        float(SECONDS_PER_HOUR),
    )
