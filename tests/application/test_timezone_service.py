"""TimezoneService tests using a hand-written fake catalog."""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo
from zoneinfo import ZoneInfo

from fancyclock.application.timezones import TimezoneEntry, TimezoneService
from fancyclock.domain.timezones import SECONDS_PER_HOUR

OFFSETS = {
    "Europe/London": 1.0 * SECONDS_PER_HOUR,
    "America/New_York": -4.0 * SECONDS_PER_HOUR,
}


class FakeCatalog:
    def all_timezones(self) -> tuple[str, ...]:
        return tuple(OFFSETS)

    def utc_offset_seconds(self, tz_id: str) -> float:
        return OFFSETS[tz_id]


def test_entries_are_formatted_and_sorted_by_display() -> None:
    service = TimezoneService(catalog=FakeCatalog())
    assert service.entries() == (
        TimezoneEntry(display="[UTC+1.0] Europe/London", tz_id="Europe/London"),
        TimezoneEntry(display="[UTC-4.0] America/New_York", tz_id="America/New_York"),
    )


class ZoneinfoCatalog(FakeCatalog):
    """Resolves zones as the alarms do; raises for an unknown one."""

    def tzinfo_for(self, tz_id: str) -> tzinfo:
        return ZoneInfo(tz_id)


def test_the_offset_at_an_instant_comes_from_the_alarm_zone_data() -> None:
    service = TimezoneService(catalog=ZoneinfoCatalog())
    instant = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
    expected = instant.astimezone(ZoneInfo("Africa/Casablanca")).utcoffset()
    offset = service.utc_offset_seconds_at("Africa/Casablanca", instant)
    assert offset == int(expected.total_seconds())


def test_an_unknown_zone_has_no_offset() -> None:
    service = TimezoneService(catalog=ZoneinfoCatalog())
    instant = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
    assert service.utc_offset_seconds_at("Nowhere/Atlantis", instant) is None
    assert service.utc_offset_seconds_at("", instant) is None
