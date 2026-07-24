"""Domain locale normalisation tests."""

from __future__ import annotations

from fancyclock.domain.locales import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    is_supported,
    language_of,
    normalize_locale,
)


def test_supported_catalog_contains_default() -> None:
    assert DEFAULT_LOCALE in SUPPORTED_LOCALES


def test_is_supported() -> None:
    assert is_supported("fr_FR")
    assert not is_supported("xx_XX")


def test_language_of() -> None:
    assert language_of("fr_FR") == "fr"
    assert language_of("fr") == "fr"


def test_normalize_exact_match_with_encoding_suffix() -> None:
    assert normalize_locale("en_GB.UTF-8") == "en_GB"


def test_normalize_modifier_suffix() -> None:
    assert normalize_locale("ca_ES@valencia") == "ca_ES"


def test_normalize_dash_separator() -> None:
    assert normalize_locale("en-gb") == "en_GB"


def test_normalize_unknown_country_falls_back_to_language_variant() -> None:
    assert normalize_locale("ar_AE") == "ar_SA"


def test_normalize_bare_language() -> None:
    assert normalize_locale("fr") == "fr_FR"


def test_normalize_unknown_returns_default() -> None:
    assert normalize_locale("tlh_QO") == DEFAULT_LOCALE
    assert normalize_locale("klingon") == DEFAULT_LOCALE


def test_normalize_empty_and_none_return_default() -> None:
    assert normalize_locale("") == DEFAULT_LOCALE
    assert normalize_locale(None) == DEFAULT_LOCALE


def test_normalize_single_part_with_separator() -> None:
    assert normalize_locale("en_") == "en_US"
