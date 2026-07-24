"""JSON-file implementation of the TranslationsRepository port."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fancyclock.domain.locales import language_of

logger = logging.getLogger(__name__)

TRANSLATION_FILE_SUFFIX = ".json"


class JsonTranslationsRepository:
    """Loads translation dictionaries from per-locale JSON files."""

    def __init__(self, translations_dir: Path) -> None:
        self._translations_dir = translations_dir

    def load(self, locale_code: str) -> dict[str, Any] | None:
        """Return translations for a locale, trying its bare language too."""
        path = self._translations_dir / f"{locale_code}{TRANSLATION_FILE_SUFFIX}"
        if not path.exists():
            language = language_of(locale_code)
            fallback = self._translations_dir / (f"{language}{TRANSLATION_FILE_SUFFIX}")
            if not fallback.exists():
                return None
            path = fallback

        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            logger.error("Failed to load locale %s: %s", locale_code, exc)
            return None

        return data if isinstance(data, dict) else None
