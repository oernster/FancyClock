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


SECONDS_PER_MINUTE = 60
KATHMANDU = 5 * SECONDS_PER_HOUR + 45 * SECONDS_PER_MINUTE
CHATHAM = 13 * SECONDS_PER_HOUR + 45 * SECONDS_PER_MINUTE
MARQUESAS = -(9 * SECONDS_PER_HOUR + 30 * SECONDS_PER_MINUTE)


def test_a_quarter_hour_offset_is_stated_exactly() -> None:
    assert format_offset_label(KATHMANDU) == "UTC+5.75"
    assert format_offset_label(CHATHAM) == "UTC+13.75"


def test_whole_and_half_hour_labels_keep_their_one_decimal() -> None:
    assert format_offset_label(MARQUESAS) == "UTC-9.5"
    assert format_offset_label(-10 * SECONDS_PER_HOUR) == "UTC-10.0"


def test_format_timezone_entry() -> None:
    assert (
        format_timezone_entry("Europe/London", SECONDS_PER_HOUR)
        == "[UTC+1.0] Europe/London"
    )
