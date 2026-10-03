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


def test_a_script_subtag_is_read_through_to_the_region() -> None:
    assert normalize_locale("zh-Hant-TW") == "zh_TW"
    assert normalize_locale("zh-Hans-CN") == "zh_CN"
    assert normalize_locale("zh_Hant_HK") == "zh_TW"


def test_a_script_alone_picks_the_variant_written_in_it() -> None:
    assert normalize_locale("zh-Hant") == "zh_TW"
    assert normalize_locale("zh-Hans") == "zh_CN"


def test_the_norwegian_macrolanguage_reads_as_bokmal() -> None:
    assert normalize_locale("no_NO") == "nb_NO"
    assert normalize_locale("no") == "nb_NO"


def test_windows_bcp47_names_resolve_to_their_locale() -> None:
    assert normalize_locale("fr-FR") == "fr_FR"
    assert normalize_locale("de-DE") == "de_DE"
    assert normalize_locale("ja-JP") == "ja_JP"
