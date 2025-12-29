"""Non-core helpers for `LocaleDetector`.

This file exists so `localization/locale_detector.py` stays under 350 lines.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class LocaleDetectorExtrasMixin:
    """Extra helper methods for `LocaleDetector`."""

    def get_supported_locales(self) -> List[str]:
        """Get list of all supported locale codes."""
        return list(self.SUPPORTED_LOCALES.keys())

    @classmethod
    def get_sorted_locales(cls) -> List[tuple]:
        """Return supported locales with info sorted by country code."""
        sorted_items = []
        for locale_code, locale_info in cls.SUPPORTED_LOCALES.items():
            country_code = (
                locale_code.split("_")[1] if "_" in locale_code else locale_code
            )
            flag = cls._get_flag_emoji(country_code)

            enhanced_info = locale_info.copy()
            enhanced_info["flag"] = flag
            sorted_items.append((locale_code, enhanced_info))

        sorted_items.sort(key=lambda x: x[0].split("_")[1] if "_" in x[0] else x[0])
        return sorted_items

    @classmethod
    def _get_flag_emoji(cls, country_code: str) -> str:
        """Return a non-emoji country marker like '[GB]'."""
        if not country_code:
            return "[]"

        safe_code = "".join(ch for ch in country_code.upper() if ch.isalpha())
        if len(safe_code) != 2:
            return "[]"
        return f"[{safe_code}]"

    def get_locale_info(self, locale_code: str) -> Optional[Dict[str, str]]:
        """Get information about a specific locale."""
        return self.SUPPORTED_LOCALES.get(locale_code)

    def get_locales_by_batch(self, batch_number: int) -> List[str]:
        """Return locale codes in the given batch."""
        return [
            locale_code
            for locale_code, info in self.SUPPORTED_LOCALES.items()
            if info["batch"] == batch_number
        ]

    def get_batch_info(self) -> Dict[int, Dict[str, Any]]:
        """Get information about all batches."""
        from . import BATCH_INFO

        return BATCH_INFO

    def find_best_match(self, preferred_locales: List[str]) -> str:
        """Find best supported locale from a list of preferences."""
        for preferred in preferred_locales:
            normalized = self._normalize_locale(preferred)
            if self.is_supported(normalized):
                return normalized

        return self.DEFAULT_LOCALE

    def get_language_variants(self, language_code: str) -> List[str]:
        """Get all supported variants of a language (e.g. en_*)."""
        language_code = language_code.lower()
        return [
            locale_code
            for locale_code in self.SUPPORTED_LOCALES
            if locale_code.startswith(f"{language_code}_")
        ]

    def get_rtl_locales(self) -> List[str]:
        """Return list of right-to-left (RTL) locales."""
        rtl_languages = ["ar", "he", "fa", "ur"]
        return [
            locale_code
            for locale_code in self.SUPPORTED_LOCALES
            if any(locale_code.startswith(f"{lang}_") for lang in rtl_languages)
        ]

    def is_rtl(self, locale_code: str) -> bool:
        """Return True if locale uses right-to-left text direction."""
        return locale_code in self.get_rtl_locales()

    @classmethod
    def get_locale_info_with_country_marker(
        cls, locale_code: str
    ) -> Optional[Dict[str, str]]:
        """Get locale info augmented with a country marker."""
        if locale_code not in cls.SUPPORTED_LOCALES:
            return None

        info = cls.SUPPORTED_LOCALES[locale_code].copy()
        country_code = locale_code.split("_")[1] if "_" in locale_code else locale_code
        info["flag"] = cls._get_flag_emoji(country_code)
        return info

    @classmethod
    def get_country_from_locale(cls, locale_code: str) -> str:
        """Extract country code from locale code."""
        if "_" in locale_code:
            return locale_code.split("_")[1]
        return "GB"
