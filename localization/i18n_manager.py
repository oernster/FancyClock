import json
import logging
import locale as _locale
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import date, datetime

from .locale_detector import LocaleDetector
from .timezone_translator import TimezoneTranslator


logger = logging.getLogger(__name__)


class LocalizationManager:
    def __init__(
        self,
        default_locale: Optional[str] = None,
        translations_dir: Optional[Union[str, Path]] = None,
    ):
        # Use LocaleDetector everywhere so we always normalise things like
        # "English_United Kingdom" -> "en_GB"
        self.locale_detector = LocaleDetector()

        if default_locale:
            # Normalise whatever the caller gave us
            try:
                normalized_locale = self.locale_detector._normalize_locale(default_locale)
            except Exception:
                normalized_locale = self.locale_detector.DEFAULT_LOCALE
        else:
            # Detect from system
            try:
                normalized_locale = self.locale_detector.detect_system_locale()
            except Exception:
                normalized_locale = self.locale_detector.DEFAULT_LOCALE

        self._current_locale = normalized_locale

        # Where translations live
        self.translations_dir = (
            Path(translations_dir)
            if translations_dir
            else Path(__file__).parent / "translations"
        )

        # Cache: { locale: translation_dict }
        self._translations_cache: Dict[str, Dict[str, Any]] = {}

        # Helpers for timezone / locale-aware strings
        self.timezone_translator = TimezoneTranslator(self._current_locale)

        # Ensure translations for the starting locale are loaded
        self.set_locale(self._current_locale)

    @property
    def current_locale(self) -> str:
        return self._current_locale

    # ----------------------------------------------------------------------
    # Load translation JSON
    # ----------------------------------------------------------------------
    def _load_locale_translations(self, locale_code: str) -> bool:
        if locale_code in self._translations_cache:
            return True

        # try full locale
        path = self.translations_dir / f"{locale_code}.json"
        if not path.exists():
            # try language-only
            lang = locale_code.split("_")[0]
            path2 = self.translations_dir / f"{lang}.json"
            if path2.exists():
                path = path2
            else:
                return False

        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    self._translations_cache[locale_code] = data
                    return True
        except Exception as e:
            logger.error(f"Failed to load locale {locale_code}: {e}")

        return False

    # ----------------------------------------------------------------------
    # Public: Set locale
    # ----------------------------------------------------------------------
    def set_locale(self, locale_code: str) -> bool:
        if not locale_code:
            return False

        # Normalise using LocaleDetector so things like
        # "English_United Kingdom" / "en-gb" / "en_GB.UTF-8" work.
        if hasattr(self, "locale_detector") and locale_code:
            try:
                locale_code = self.locale_detector._normalize_locale(locale_code)
            except Exception:
                # If anything goes wrong, just use the raw code
                pass

        # Try full locale first (e.g. en_GB, en_US, fr_FR)
        if not self._load_locale_translations(locale_code):
            # Fallback to language-only (e.g. "en", "fr")
            lang = locale_code.split("_")[0]
            if not self._load_locale_translations(lang):
                logger.warning(f"No translations for locale {locale_code}")
                return False
            locale_code = lang

        self._current_locale = locale_code

        # Keep timezone translator in sync
        if hasattr(self, "timezone_translator"):
            self.timezone_translator.locale = self._current_locale

        # Best-effort: adjust LC_TIME
        try:
            _locale.setlocale(_locale.LC_TIME, locale_code.replace("_", "-"))
        except Exception:
            pass

        return True

    # ----------------------------------------------------------------------
    # Lookup value in JSON
    # ----------------------------------------------------------------------
    def get_translation(self, key: str, locale: Optional[str] = None) -> str:
        loc = locale or self._current_locale

        # ensure loaded
        if loc not in self._translations_cache:
            self._load_locale_translations(loc)

        data = self._translations_cache.get(loc, {})

        if key in data:
            return data[key]

        # fallback to last segment
        if "." in key:
            short = key.split(".")[-1]
            if short in data:
                return data[short]

        # final fallback: key itself
        return key

    # ----------------------------------------------------------------------
    # DIGIT / NUMERAL FORMATTING (JSON-DRIVEN)
    # ----------------------------------------------------------------------
    def _get_digit_map(self, locale_code: Optional[str] = None) -> Optional[list]:
        loc = locale_code or self._current_locale

        data = self._translations_cache.get(loc)
        if not data:
            return None

        digits = data.get("digits")
        if isinstance(digits, list) and len(digits) == 10:
            return digits

        return None

    def format_number(self, value: Union[int, str, float], locale_code: Optional[str] = None) -> str:
        s = str(value)

        digit_map = self._get_digit_map(locale_code)
        if not digit_map:
            return s  # Western digits fallback

        # translate 0–9 → native digits
        output = []
        for ch in s:
            if ch.isdigit():
                output.append(digit_map[int(ch)])
            else:
                output.append(ch)
        return "".join(output)

    # ----------------------------------------------------------------------
    # WEEKDAY & MONTH ABBREVIATIONS
    # ----------------------------------------------------------------------
    def get_weekday_abbr(self, dt: Union[date, datetime]) -> str:
        # Monday=1..Sunday=7 for Qt
        try:
            if hasattr(dt, "dayOfWeek"):
                wd = int(dt.dayOfWeek())
            elif isinstance(dt, datetime):
                wd = dt.weekday() + 1
            else:
                wd = dt.weekday() + 1
        except:
            wd = 1

        keys = {
            1: "calendar.days.monday",
            2: "calendar.days.tuesday",
            3: "calendar.days.wednesday",
            4: "calendar.days.thursday",
            5: "calendar.days.friday",
            6: "calendar.days.saturday",
            7: "calendar.days.sunday",
        }
        return self.get_translation(keys.get(wd, "calendar.days.monday"))

    def get_month_abbr(self, dt: Union[date, datetime]) -> str:
        try:
            m = dt.month() if hasattr(dt, "month") else dt.month
        except:
            m = 1

        names = [
            "january","february","march","april","may","june",
            "july","august","september","october","november","december"
        ]
        key = names[m - 1]
        return self.get_translation(key)

    # ----------------------------------------------------------------------
    # DIGITAL CLOCK DATE STRING
    # ----------------------------------------------------------------------
    def format_date_fancy(self, dt: Union[date, datetime]) -> str:
        wd = self.get_weekday_abbr(dt)

        # Ensure weekday is always 3 characters wide
        if len(wd) > 3:
            wd = wd[:3]
        elif len(wd) < 3:
            wd = wd.ljust(3)

        day = self.format_number(dt.day())
        mon = self.get_month_abbr(dt)
        return f"{wd} {day} {mon}"

