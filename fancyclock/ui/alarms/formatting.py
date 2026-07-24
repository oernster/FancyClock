"""Localised display formatting shared by the alarm UI."""

from __future__ import annotations

from datetime import datetime, tzinfo

from PySide6.QtGui import QColor, QIcon, QPixmap

from fancyclock.domain.alarms import MINUTES_PER_HOUR, Alarm

COLOR_DOT_PX = 14

WEEKDAY_KEYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
DAY_SEPARATOR = " "


def time_text(i18n, hour: int, minute: int) -> str:
    """Return HH:MM with locale digits."""
    return i18n.format_number(f"{hour:02d}:{minute:02d}")


def duration_text(i18n, minutes: int) -> str:
    """Return a compact duration such as ``5 min`` or ``2 h``."""
    if minutes < MINUTES_PER_HOUR:
        suffix = i18n.get_translation("minutes_suffix")
        return f"{i18n.format_number(minutes)} {suffix}"
    hours = minutes // MINUTES_PER_HOUR
    suffix = i18n.get_translation("hours_suffix")
    return f"{i18n.format_number(hours)} {suffix}"


def days_text(i18n, alarm: Alarm) -> str:
    """Return the repeat-days summary or the one-off date."""
    if alarm.one_off_date is not None:
        return alarm.one_off_date.isoformat()
    return DAY_SEPARATOR.join(
        i18n.get_translation(WEEKDAY_KEYS[day]) for day in alarm.weekdays
    )


def occurrence_text(i18n, occurrence_utc: datetime, tz: tzinfo) -> str:
    """Return a short local date-and-time for an occurrence."""
    local = occurrence_utc.astimezone(tz)
    stamp = f"{local.year:04d}-{local.month:02d}-{local.day:02d}"
    clock = time_text(i18n, local.hour, local.minute)
    return f"{stamp} {clock}"


def color_dot_icon(hex_value: str) -> QIcon:
    """Return a small filled-circle icon in the given colour."""
    pixmap = QPixmap(COLOR_DOT_PX, COLOR_DOT_PX)
    pixmap.fill(QColor(hex_value))
    return QIcon(pixmap)
