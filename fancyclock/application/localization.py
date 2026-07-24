"""Localization service: translations, native digits and fancy dates.

Translation data is loaded through the TranslationsRepository port; the
locale-normalisation rules live in the domain layer. Date arguments are
duck-typed so both ``datetime.date`` and Qt's ``QDate`` work without this
layer importing Qt.
"""

from __future__ import annotations

from typing import Any

from fancyclock.application.ports import (
    SystemLocaleProbe,
    TimezoneLocaleMap,
    TranslationsRepository,
)
from fancyclock.domain.dates import (
    FALLBACK_MONTH,
    FALLBACK_WEEKDAY,
    compose_fancy_date,
    month_translation_key,
    weekday_translation_key,
)
from fancyclock.domain.digits import translate_digits, valid_digit_map
from fancyclock.domain.locales import (
    DEFAULT_LOCALE,
    language_of,
    normalize_locale,
)

DIGITS_TRANSLATION_KEY = "digits"
TIMEZONE_FALLBACK_LOCALE = "en_US"


def _duck_weekday(dt: Any) -> int:
    """Return an ISO weekday from a QDate-like or datetime-like object."""
    try:
        if hasattr(dt, "dayOfWeek"):
            return int(dt.dayOfWeek())
        return dt.weekday() + 1
    except Exception:
        return FALLBACK_WEEKDAY


def _duck_month(dt: Any) -> int:
    """Return a month number from a QDate-like or datetime-like object."""
    try:
        month = dt.month
        return int(month() if callable(month) else month)
    except Exception:
        return FALLBACK_MONTH


def _duck_day(dt: Any) -> int:
    """Return a day of month from a QDate-like or datetime-like object."""
    day = dt.day
    return int(day() if callable(day) else day)


class LocalizationService:
    """Loads translations and formats localized text for the UI."""

    def __init__(
        self,
        translations: TranslationsRepository,
        tz_locale_map: TimezoneLocaleMap,
        system_probe: SystemLocaleProbe,
        default_locale: str | None = None,
    ) -> None:
        self._translations = translations
        self._tz_locale_map = tz_locale_map
        self._system_probe = system_probe
        self._cache: dict[str, dict[str, Any]] = {}

        if default_locale:
            initial = normalize_locale(default_locale)
        else:
            initial = self.detect_system_locale()
        self._current_locale = initial
        self.set_locale(initial)

    @property
    def current_locale(self) -> str:
        """Return the active locale code."""
        return self._current_locale

    # ------------------------------------------------------------------
    # Locale selection
    # ------------------------------------------------------------------
    def detect_system_locale(self) -> str:
        """Detect the best supported locale for this system.

        The first non-empty probe candidate wins; the timezone-to-locale
        map is consulted only when the system reports no locale at all.
        """
        for candidate in self._system_probe.candidates():
            if candidate:
                return normalize_locale(candidate)
        mapped = self.locale_for_timezone(None)
        if mapped:
            return mapped
        return DEFAULT_LOCALE

    def locale_for_timezone(self, tz_id: str | None) -> str | None:
        """Return the normalized locale mapped to a timezone, or ``None``."""
        mapped = self._tz_locale_map.locale_for(tz_id)
        if mapped:
            return normalize_locale(mapped)
        return None

    def locale_for_timezone_or_fallback(self, tz_id: str) -> str:
        """Return the locale for a timezone, falling back for unmapped zones."""
        return self.locale_for_timezone(tz_id) or TIMEZONE_FALLBACK_LOCALE

    def set_locale(self, locale_code: str) -> bool:
        """Activate a locale, falling back to its bare language when needed."""
        if not locale_code:
            return False

        locale_code = normalize_locale(locale_code)

        if not self._ensure_loaded(locale_code):
            language = language_of(locale_code)
            if not self._ensure_loaded(language):
                return False
            locale_code = language

        self._current_locale = locale_code
        return True

    def _ensure_loaded(self, locale_code: str) -> bool:
        """Load translations for ``locale_code`` into the cache."""
        if locale_code in self._cache:
            return True
        data = self._translations.load(locale_code)
        if data is None:
            return False
        self._cache[locale_code] = data
        return True

    # ------------------------------------------------------------------
    # Translation lookup and formatting
    # ------------------------------------------------------------------
    def get_translation(self, key: str, locale: str | None = None) -> str:
        """Return the translated text for ``key``, or the key itself."""
        loc = locale or self._current_locale
        self._ensure_loaded(loc)
        data = self._cache.get(loc, {})

        if key in data:
            return data[key]

        if "." in key:
            short = key.split(".")[-1]
            if short in data:
                return data[short]

        return key

    def _digit_map(self, locale: str | None) -> tuple[str, ...] | None:
        loc = locale or self._current_locale
        data = self._cache.get(loc)
        if not data:
            return None
        return valid_digit_map(data.get(DIGITS_TRANSLATION_KEY))

    def format_number(self, value: int | float | str, locale: str | None = None) -> str:
        """Render a number using the locale's native digits when defined."""
        return translate_digits(str(value), self._digit_map(locale))

    def get_weekday_abbr(self, dt: Any) -> str:
        """Return the translated weekday abbreviation for a date."""
        return self.get_translation(weekday_translation_key(_duck_weekday(dt)))

    def get_month_abbr(self, dt: Any) -> str:
        """Return the translated month abbreviation for a date."""
        return self.get_translation(month_translation_key(_duck_month(dt)))

    def format_date_fancy(self, dt: Any) -> str:
        """Return the digital clock date line for a date."""
        return compose_fancy_date(
            self.get_weekday_abbr(dt),
            self.format_number(_duck_day(dt)),
            self.get_month_abbr(dt),
        )
