"""Domain date-presentation tests."""

from __future__ import annotations

from fancyclock.domain.dates import (
    WEEKDAY_ABBR_WIDTH,
    compose_fancy_date,
    fixed_width_weekday,
    month_translation_key,
    weekday_translation_key,
)


def test_weekday_translation_key_known_and_fallback() -> None:
    assert weekday_translation_key(1) == "calendar.days.monday"
    assert weekday_translation_key(7) == "calendar.days.sunday"
    assert weekday_translation_key(99) == "calendar.days.monday"


def test_month_translation_key_known_and_fallback() -> None:
    assert month_translation_key(1) == "january"
    assert month_translation_key(12) == "december"
    assert month_translation_key(0) == "january"
    assert month_translation_key(13) == "january"


def test_fixed_width_weekday_trims_and_pads() -> None:
    assert fixed_width_weekday("Monday") == "Mon"
    assert fixed_width_weekday("Mo") == "Mo "
    assert len(fixed_width_weekday("x")) == WEEKDAY_ABBR_WIDTH


def test_compose_fancy_date() -> None:
    assert compose_fancy_date("Monday", "20", "Jul") == "Mon 20 Jul"
