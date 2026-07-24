"""Domain timezone formatting tests."""

from __future__ import annotations

from fancyclock.domain.timezones import (
    SECONDS_PER_HOUR,
    format_offset_label,
    format_timezone_entry,
)


def test_format_offset_label_positive_and_negative() -> None:
    assert format_offset_label(SECONDS_PER_HOUR) == "UTC+1.0"
    assert format_offset_label(-5.5 * SECONDS_PER_HOUR) == "UTC-5.5"
    assert format_offset_label(0) == "UTC+0.0"


def test_format_timezone_entry() -> None:
    assert (
        format_timezone_entry("Europe/London", SECONDS_PER_HOUR)
        == "[UTC+1.0] Europe/London"
    )
