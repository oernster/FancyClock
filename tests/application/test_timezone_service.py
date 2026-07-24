"""TimezoneService tests using a hand-written fake catalog."""

from __future__ import annotations

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
