"""Pure formatting rules for timezone listing entries."""

from __future__ import annotations

SECONDS_PER_HOUR = 3600


def format_offset_label(offset_seconds: float) -> str:
    """Return a UTC offset label such as ``UTC+1.0`` for the given seconds."""
    offset_hours = offset_seconds / SECONDS_PER_HOUR
    return f"UTC{offset_hours:+.1f}"


def format_timezone_entry(tz_id: str, offset_seconds: float) -> str:
    """Return the display text for one timezone list entry."""
    return f"[{format_offset_label(offset_seconds)}] {tz_id}"
