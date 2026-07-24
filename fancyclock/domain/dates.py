"""Pure date-presentation rules for the digital clock."""

from __future__ import annotations

WEEKDAY_ABBR_WIDTH = 3

FALLBACK_WEEKDAY = 1
FALLBACK_MONTH = 1

WEEKDAY_TRANSLATION_KEYS: dict[int, str] = {
    1: "calendar.days.monday",
    2: "calendar.days.tuesday",
    3: "calendar.days.wednesday",
    4: "calendar.days.thursday",
    5: "calendar.days.friday",
    6: "calendar.days.saturday",
    7: "calendar.days.sunday",
}

MONTH_TRANSLATION_KEYS: tuple[str, ...] = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


def weekday_translation_key(weekday: int) -> str:
    """Return the translation key for an ISO weekday (Monday=1..Sunday=7)."""
    return WEEKDAY_TRANSLATION_KEYS.get(
        weekday, WEEKDAY_TRANSLATION_KEYS[FALLBACK_WEEKDAY]
    )


def month_translation_key(month: int) -> str:
    """Return the translation key for a month number (January=1)."""
    if 1 <= month <= len(MONTH_TRANSLATION_KEYS):
        return MONTH_TRANSLATION_KEYS[month - 1]
    return MONTH_TRANSLATION_KEYS[FALLBACK_MONTH - 1]


def fixed_width_weekday(abbr: str) -> str:
    """Trim or pad a weekday abbreviation to WEEKDAY_ABBR_WIDTH characters."""
    if len(abbr) > WEEKDAY_ABBR_WIDTH:
        return abbr[:WEEKDAY_ABBR_WIDTH]
    return abbr.ljust(WEEKDAY_ABBR_WIDTH)


def compose_fancy_date(weekday: str, day: str, month: str) -> str:
    """Assemble the digital clock date string from translated parts."""
    return f"{fixed_width_weekday(weekday)} {day} {month}"
