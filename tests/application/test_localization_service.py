"""LocalizationService tests using hand-written fakes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fancyclock.application.localization import (
    TIMEZONE_FALLBACK_LOCALE,
    LocalizationService,
)
from fancyclock.domain.locales import DEFAULT_LOCALE

ARABIC_DIGITS = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"]


class FakeTranslations:
    def __init__(self, data: dict[str, dict[str, Any]]):
        self._data = data
        self.load_calls: list[str] = []

    def load(self, locale_code: str) -> dict[str, Any] | None:
        self.load_calls.append(locale_code)
        return self._data.get(locale_code)


class FakeTzMap:
    def __init__(self, mapping: dict[str, str]):
        self._mapping = mapping

    def locale_for(self, tz_id: str | None) -> str | None:
        return self._mapping.get(tz_id or "SYSTEM")


class FakeProbe:
    def __init__(self, candidates: tuple[str, ...]):
        self._candidates = candidates

    def candidates(self) -> tuple[str, ...]:
        return self._candidates


class QDateLike:
    """Duck-typed stand-in for QDate."""

    def __init__(self, weekday: int, day: int, month: int):
        self._weekday = weekday
        self._day = day
        self._month = month

    def dayOfWeek(self) -> int:  # noqa: N802 (Qt naming)
        return self._weekday

    def day(self) -> int:
        return self._day

    def month(self) -> int:
        return self._month


class BrokenDate:
    """Raises on every date accessor except ``day``."""

    day = 5

    def dayOfWeek(self) -> int:  # noqa: N802 (Qt naming)
        raise RuntimeError("boom")

    @property
    def month(self):
        raise RuntimeError("boom")


def build_service(
    data: dict[str, dict[str, Any]] | None = None,
    tz_mapping: dict[str, str] | None = None,
    candidates: tuple[str, ...] = ("en_GB",),
    default_locale: str | None = "en_GB",
) -> LocalizationService:
    return LocalizationService(
        translations=FakeTranslations(data if data is not None else {"en_GB": {}}),
        tz_locale_map=FakeTzMap(tz_mapping or {}),
        system_probe=FakeProbe(candidates),
        default_locale=default_locale,
    )


def test_init_with_explicit_default_locale() -> None:
    service = build_service(data={"en_GB": {"app_name": "Fancy Clock"}})
    assert service.current_locale == "en_GB"
    assert service.get_translation("app_name") == "Fancy Clock"


def test_detection_uses_first_nonempty_probe_candidate() -> None:
    service = build_service(
        data={"fr_FR": {}},
        candidates=("", "fr_FR.UTF-8"),
        default_locale=None,
    )
    assert service.current_locale == "fr_FR"


def test_detection_falls_back_to_timezone_map() -> None:
    service = build_service(
        data={"de_DE": {}},
        tz_mapping={"SYSTEM": "de_DE"},
        candidates=(),
        default_locale=None,
    )
    assert service.current_locale == "de_DE"


def test_detection_falls_back_to_default_locale() -> None:
    service = build_service(data={}, candidates=(), default_locale=None)
    assert service.current_locale == DEFAULT_LOCALE


def test_set_locale_rejects_empty() -> None:
    service = build_service()
    assert service.set_locale("") is False


def test_set_locale_language_fallback() -> None:
    service = build_service(data={"en_GB": {}, "fr": {"help": "Aide"}})
    assert service.set_locale("fr_FR") is True
    assert service.current_locale == "fr"
    assert service.get_translation("help") == "Aide"


def test_set_locale_totally_unknown_returns_false() -> None:
    service = build_service(data={"en_GB": {}})
    assert service.set_locale("de_DE") is False
    assert service.current_locale == "en_GB"


def test_get_translation_dotted_key_fallback() -> None:
    service = build_service(data={"en_GB": {"monday": "Mon"}})
    assert service.get_translation("calendar.days.monday") == "Mon"


def test_get_translation_missing_returns_key() -> None:
    service = build_service()
    assert service.get_translation("nope") == "nope"


def test_get_translation_with_explicit_uncached_locale() -> None:
    service = build_service(data={"en_GB": {}, "es_ES": {"help": "Ayuda"}})
    assert service.get_translation("help", "es_ES") == "Ayuda"


def test_format_number_with_native_digits() -> None:
    service = build_service(data={"en_GB": {"digits": ARABIC_DIGITS}})
    assert service.format_number("12:03") == "١٢:٠٣"
    assert service.format_number(7) == "٧"


def test_format_number_without_digit_map() -> None:
    service = build_service(data={"en_GB": {}})
    assert service.format_number(12) == "12"


def test_format_number_with_invalid_digit_map() -> None:
    service = build_service(data={"en_GB": {"digits": ["0", "1"]}})
    assert service.format_number(12) == "12"


def test_format_number_for_unloaded_locale() -> None:
    service = build_service(data={"en_GB": {}})
    assert service.format_number(3, "zz_ZZ") == "3"


def test_weekday_abbr_from_datetime_and_qdate() -> None:
    service = build_service(
        data={"en_GB": {"calendar.days.monday": "Mon", "calendar.days.sunday": "Sun"}}
    )
    monday = datetime(2026, 7, 20)
    assert service.get_weekday_abbr(monday) == "Mon"
    assert service.get_weekday_abbr(QDateLike(7, 1, 1)) == "Sun"


def test_weekday_abbr_fallback_on_broken_object() -> None:
    service = build_service(data={"en_GB": {"calendar.days.monday": "Mon"}})
    assert service.get_weekday_abbr(BrokenDate()) == "Mon"


def test_month_abbr_from_date_and_qdate_and_broken() -> None:
    service = build_service(data={"en_GB": {"july": "Jul", "january": "Jan"}})
    assert service.get_month_abbr(date(2026, 7, 20)) == "Jul"
    assert service.get_month_abbr(QDateLike(1, 1, 7)) == "Jul"
    assert service.get_month_abbr(BrokenDate()) == "Jan"


def test_format_date_fancy_trims_and_pads_weekday() -> None:
    service = build_service(
        data={
            "en_GB": {"calendar.days.monday": "Monday", "july": "Jul"},
        }
    )
    assert service.format_date_fancy(datetime(2026, 7, 20)) == "Mon 20 Jul"

    service_short = build_service(
        data={"en_GB": {"calendar.days.monday": "Mo", "july": "Jul"}}
    )
    assert service_short.format_date_fancy(datetime(2026, 7, 20)) == "Mo  20 Jul"


def test_locale_for_timezone_mapping_and_fallback() -> None:
    service = build_service(
        tz_mapping={"America/New_York": "en_US", "Asia/Dubai": "ar_AE"}
    )
    assert service.locale_for_timezone("America/New_York") == "en_US"
    assert service.locale_for_timezone("Asia/Dubai") == "ar_SA"
    assert service.locale_for_timezone("Atlantis/Nowhere") is None
    assert (
        service.locale_for_timezone_or_fallback("Atlantis/Nowhere")
        == TIMEZONE_FALLBACK_LOCALE
    )
