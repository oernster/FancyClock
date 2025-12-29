"""
Locale Detection System for Fancy Clock

This module provides comprehensive locale detection and management capabilities
for the Fancy Clock application, supporting 13 major international languages.
"""

import json
import locale
import logging
import os
from pathlib import Path

import tzlocal
from typing import Dict, Optional

from .locale_catalog import SUPPORTED_LOCALES
from .locale_detector_extras import LocaleDetectorExtrasMixin

logger = logging.getLogger(__name__)


class LocaleDetector(LocaleDetectorExtrasMixin):
    """
    Detects and manages locale information for the Fancy Clock application.

    Supports 32 major international languages with comprehensive
    locale detection, validation, and information retrieval.
    """

    # Default locale
    DEFAULT_LOCALE = "en_GB"

    # Major International Languages - 32 core languages including UK English
    SUPPORTED_LOCALES = SUPPORTED_LOCALES

    def __init__(self):
        """Initialize the locale detector."""
        self._system_locale = None
        self._detected_locale = None
        self._timezone_map = self._load_timezone_map()

    def _load_timezone_map(self) -> Dict[str, str]:
        """Loads the timezone-to-locale mapping from the JSON file."""
        try:
            map_path = Path(__file__).parent.parent / "timezone_locale_map.json"
            with open(map_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load timezone map: {e}")
            return {}

    def get_locale_from_timezone(self, tz_id: Optional[str] = None) -> Optional[str]:
        """
        Get the locale from a given timezone or the system's timezone.

        Args:
            tz_id (Optional[str]):
                The timezone ID to look up. If None, detects system timezone.

        Returns:
            Optional[str]: The detected locale code or None.
        """
        try:
            tz_name = tz_id or tzlocal.get_localzone_name()
            if tz_name in self._timezone_map:
                return self._timezone_map[tz_name]
        except Exception as e:
            logger.warning("Could not determine locale from timezone: %s", e)
        return None

    def detect_system_locale(self) -> str:
        """
        Detect the system's current locale.

        Returns:
            str: Detected locale code or 'en_US' as fallback
        """
        if self._system_locale:
            return self._system_locale

        try:
            # Try multiple methods to detect system locale
            detected = None

            # Method 1: Python locale module
            try:
                system_locale = locale.getdefaultlocale()[0]
                if system_locale:
                    detected = self._normalize_locale(system_locale)
            except Exception:
                pass

            # Method 2: Timezone detection
            if not detected:
                detected = self.get_locale_from_timezone()

            # Method 3: Environment variables
            if not detected:
                for env_var in ["LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"]:
                    env_locale = os.environ.get(env_var)
                    if env_locale:
                        detected = self._normalize_locale(env_locale.split(":")[0])
                        break

            # Method 4: Windows specific
            if not detected and os.name == "nt":
                try:
                    import ctypes

                    windll = ctypes.windll.kernel32
                    windll.GetUserDefaultUILanguage()
                    # This is a simplified approach.
                    # In practice you'd map the language ID.
                    detected = "en_GB"
                except Exception:
                    pass

            # Validate detected locale
            if detected and self.is_supported(detected):
                self._system_locale = detected
            else:
                self._system_locale = "en_GB"  # Safe fallback

        except Exception as e:
            logger.warning(f"Failed to detect system locale: {e}")
            self._system_locale = "en_GB"

        return self._system_locale

    def _normalize_locale(self, locale_str: str) -> str:
        """
        Normalize a locale string to our standard format.

        Args:
            locale_str: Raw locale string

        Returns:
            str: Normalized locale code
        """
        if not locale_str:
            return "en_GB"

        # Remove encoding and other suffixes
        locale_str = locale_str.split(".")[0].split("@")[0]

        # Handle different formats
        if "_" in locale_str:
            parts = locale_str.split("_")
            if len(parts) >= 2:
                lang = parts[0].lower()
                country = parts[1].upper()
                normalized = f"{lang}_{country}"

                # Map common variations to our supported locales
                if normalized in self.SUPPORTED_LOCALES:
                    return normalized

                # Try language-only mapping
                for supported in self.SUPPORTED_LOCALES:
                    if supported.startswith(f"{lang}_"):
                        return supported

        elif "-" in locale_str:
            # Handle dash format (e.g., en-US)
            parts = locale_str.split("-")
            if len(parts) >= 2:
                lang = parts[0].lower()
                country = parts[1].upper()
                normalized = f"{lang}_{country}"

                if normalized in self.SUPPORTED_LOCALES:
                    return normalized

        # Language-only fallback
        lang = locale_str.lower()
        for supported in self.SUPPORTED_LOCALES:
            if supported.startswith(f"{lang}_"):
                return supported

        return "en_GB"

    def is_supported(self, locale_code: str) -> bool:
        """
        Check if a locale is supported.

        Args:
            locale_code: Locale code to check

        Returns:
            bool: True if locale is supported
        """
        return locale_code in self.SUPPORTED_LOCALES
