from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pytz
from babel.dates import get_timezone_name


@dataclass
class TimezoneTranslator:
    """Resolve localized display names for time zones."""

    locale: str

    def get_display_name(self, tz_id: str, dt: Optional[datetime] = None) -> str:
        """Return the localized display name for a time zone.

        Args:
            tz_id: The time zone ID (e.g. 'America/New_York').
            dt: Optional datetime to resolve DST vs standard names.

        Returns:
            Localized time zone name.
        """
        tz = pytz.timezone(tz_id)

        if dt is None:
            aware_dt = datetime.now(tz)
        else:
            aware_dt = dt
            if aware_dt.tzinfo is None:
                aware_dt = tz.localize(aware_dt)
            else:
                aware_dt = aware_dt.astimezone(tz)

        return get_timezone_name(aware_dt, locale=self.locale, width="long")
