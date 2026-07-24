"""JSON-file implementation of the TimezoneLocaleMap port."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

import tzlocal

logger = logging.getLogger(__name__)


class JsonTimezoneLocaleMap:
    """Maps timezone identifiers to locale codes from a JSON file."""

    def __init__(
        self,
        map_path: Path,
        localzone_name: Callable[[], str] = tzlocal.get_localzone_name,
    ) -> None:
        self._localzone_name = localzone_name
        self._map = self._load(map_path)

    @staticmethod
    def _load(map_path: Path) -> dict[str, str]:
        try:
            with map_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.error("Failed to load timezone map: %s", exc)
            return {}

    def locale_for(self, tz_id: str | None) -> str | None:
        """Return the locale for ``tz_id`` (``None`` means the system zone)."""
        try:
            tz_name = tz_id or self._localzone_name()
        except Exception as exc:
            logger.warning("Could not determine system timezone: %s", exc)
            return None
        return self._map.get(tz_name)
