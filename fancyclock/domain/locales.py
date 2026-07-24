"""Locale catalog and pure locale normalisation rules."""

from __future__ import annotations

DEFAULT_LOCALE = "en_GB"

SUPPORTED_LOCALES: tuple[str, ...] = (
    "en_US",
    "en_GB",
    "es_ES",
    "fr_FR",
    "de_DE",
    "it_IT",
    "pt_BR",
    "ru_RU",
    "zh_CN",
    "zh_TW",
    "ja_JP",
    "ko_KR",
    "hi_IN",
    "ar_SA",
    "cs_CZ",
    "sv_SE",
    "nb_NO",
    "da_DK",
    "fi_FI",
    "nl_NL",
    "pl_PL",
    "pt_PT",
    "tr_TR",
    "uk_UA",
    "el_GR",
    "id_ID",
    "vi_VN",
    "th_TH",
    "he_IL",
    "ro_RO",
    "hu_HU",
    "hr_HR",
    "bg_BG",
    "sk_SK",
    "sl_SI",
    "fr_CA",
    "ca_ES",
    "et_EE",
    "lv_LV",
    "lt_LT",
)

_LOCALE_PARTS = 2


def is_supported(locale_code: str) -> bool:
    """Return True when the locale code is one of the supported locales."""
    return locale_code in SUPPORTED_LOCALES


def language_of(locale_code: str) -> str:
    """Return the language segment of a locale code (``fr_FR`` gives ``fr``)."""
    return locale_code.split("_")[0]


def _variant_for_language(language: str) -> str | None:
    """Return the first supported locale for a bare language code."""
    prefix = f"{language}_"
    for supported in SUPPORTED_LOCALES:
        if supported.startswith(prefix):
            return supported
    return None


def normalize_locale(locale_str: str | None) -> str:
    """Normalise a raw locale string to a supported locale code.

    Handles encodings and modifiers (``en_GB.UTF-8``), dash separators
    (``en-gb``) and bare language codes (``fr``). Unknown input falls back
    to DEFAULT_LOCALE.
    """
    if not locale_str:
        return DEFAULT_LOCALE

    locale_str = locale_str.split(".")[0].split("@")[0]

    for separator in ("_", "-"):
        if separator in locale_str:
            parts = locale_str.split(separator)
            if len(parts) >= _LOCALE_PARTS:
                lang = parts[0].lower()
                country = parts[1].upper()
                normalized = f"{lang}_{country}"
                if is_supported(normalized):
                    return normalized
                variant = _variant_for_language(lang)
                if variant:
                    return variant
            break

    variant = _variant_for_language(locale_str.lower())
    if variant:
        return variant

    return DEFAULT_LOCALE
