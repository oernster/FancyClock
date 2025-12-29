"""Number formatter for localized number systems.

Supports native number systems for different locales.
"""

import logging

logger = logging.getLogger(__name__)


class NumberFormatter:
    """Formats numbers according to locale-specific number systems."""

    def __init__(self):
        # Native number systems mapping
        self.number_systems = {
            # Arabic-Indic numerals (Arabic, Persian, Urdu)
            "ar_SA": {
                "0": "٠",
                "1": "١",
                "2": "٢",
                "3": "٣",
                "4": "٤",
                "5": "٥",
                "6": "٦",
                "7": "٧",
                "8": "٨",
                "9": "٩",
            },
            # Devanagari numerals (Hindi, Marathi, Nepali)
            "hi_IN": {
                "0": "०",
                "1": "१",
                "2": "२",
                "3": "३",
                "4": "४",
                "5": "५",
                "6": "६",
                "7": "७",
                "8": "८",
                "9": "९",
            },
            # Thai numerals
            "th_TH": {
                "0": "๐",
                "1": "๑",
                "2": "๒",
                "3": "๓",
                "4": "๔",
                "5": "๕",
                "6": "๖",
                "7": "๗",
                "8": "๘",
                "9": "๙",
            },
            # Persian numerals (used in some Persian contexts)
            # Note: Modern Persian often uses Arabic-Indic; traditional Persian numerals
            # exist too.
            # Bengali/Myanmar numerals could be added later.
        }

        # Locales that prefer native number systems in formal contexts
        self.native_number_locales = {"ar_SA", "hi_IN", "th_TH"}

        # Locales that use Western Arabic numerals but may have formatting preferences
        self.western_arabic_locales = {
            "bg_BG",
            "ca_ES",
            "cs_CZ",
            "da_DK",
            "de_DE",
            "el_GR",
            "es_ES",
            "et_EE",
            "fi_FI",
            "fr_CA",
            "fr_FR",
            "he_IL",
            "hr_HR",
            "hu_HU",
            "id_ID",
            "it_IT",
            "ja_JP",
            "ko_KR",
            "lt_LT",
            "lv_LV",
            "nb_NO",
            "nl_NL",
            "pl_PL",
            "pt_BR",
            "pt_PT",
            "ro_RO",
            "ru_RU",
            "sk_SK",
            "sl_SI",
            "sv_SE",
            "tr_TR",
            "uk_UA",
            "vi_VN",
            "zh_CN",
            "zh_TW",
        }

    def format_number(
        self, number: int, locale: str = "en_US", use_native: bool = True
    ) -> str:
        """
        Format number according to locale-specific number system

        Args:
            number: The number to format
            locale: The locale code (e.g., 'ar_SA', 'hi_IN', 'th_TH')
            use_native: Whether to use native number system if available

        Returns:
            Formatted number string
        """
        try:
            # Convert to string first
            number_str = str(number)

            # Use native number system if requested and available
            if use_native and locale in self.number_systems:
                number_map = self.number_systems[locale]
                formatted = "".join(
                    number_map.get(digit, digit) for digit in number_str
                )
                logger.debug(
                    "Formatted %s for %s: %s -> %s",
                    number,
                    locale,
                    number_str,
                    formatted,
                )
                return formatted

            # For locales with specific formatting preferences but using Western Arabic
            # numerals.
            elif locale in self.western_arabic_locales:
                # Could add thousand separators, decimal formatting, etc. here
                return number_str

            # Default to Western Arabic numerals
            else:
                return number_str

        except Exception as exc:
            logger.warning(
                "Failed to format number %s for locale %s: %s",
                number,
                locale,
                exc,
            )
            return str(number)

    def format_ordinal(self, number: int, locale: str = "en_US") -> str:
        """
        Format ordinal number according to locale

        Args:
            number: The number to format as ordinal
            locale: The locale code

        Returns:
            Formatted ordinal string
        """
        try:
            # For native number system locales, format the number first
            if locale in self.native_number_locales:
                formatted_number = self.format_number(
                    number,
                    locale,
                    use_native=True,
                )

                # Add locale-specific ordinal patterns
                if locale == "ar_SA":
                    # Arabic ordinals typically use the number with specific markers
                    # Arabic ordinals are complex; keep simple for now.
                    return f"{formatted_number}"
                elif locale == "hi_IN":
                    # Hindi ordinals
                    return (
                        f"{formatted_number}वां"
                        if number > 1
                        else f"{formatted_number}ला"
                    )
                elif locale == "th_TH":
                    # Thai ordinals
                    return f"ที่ {formatted_number}"

            # For other locales, use Western Arabic numerals with locale-appropriate
            # ordinal patterns.
            else:
                # This will be handled by the translation keys we added
                return str(number)

        except Exception as exc:
            logger.warning(
                "Failed to format ordinal %s for locale %s: %s",
                number,
                locale,
                exc,
            )
            return str(number)

    def is_native_number_locale(self, locale: str) -> bool:
        """Check if locale uses native number system"""
        return locale in self.native_number_locales

    def get_supported_locales(self) -> set:
        """Get all supported locales for number formatting"""
        return self.native_number_locales | self.western_arabic_locales


# Global instance
_number_formatter = NumberFormatter()


def format_number(number: int, locale: str = "en_US", use_native: bool = True) -> str:
    """Global function to format numbers."""
    return _number_formatter.format_number(number, locale, use_native)


def format_ordinal(number: int, locale: str = "en_US") -> str:
    """Global function to format ordinals."""
    return _number_formatter.format_ordinal(number, locale)


def is_native_number_locale(locale: str) -> bool:
    """Global function to check if locale uses native numbers."""
    return _number_formatter.is_native_number_locale(locale)
