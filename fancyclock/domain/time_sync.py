"""Pure clock-offset arithmetic."""

from __future__ import annotations

from datetime import datetime


def clock_offset_seconds(reference_utc: datetime, local_utc: datetime) -> float:
    """Return the offset between a reference clock and the local clock."""
    return (reference_utc - local_utc).total_seconds()
