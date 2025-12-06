"""
Configuration and helper utilities for timezone translation.

Contains:
- LANGUAGE_FALLBACKS: fallback mapping for rare languages.
- UNSUPPORTED_FALLBACKS: mapping for languages not supported by LibreTranslate.
- resolve_target_lang: determine which LibreTranslate language code to use.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Set


# Your explicit fallbacks
LANGUAGE_FALLBACKS: Dict[str, str] = {
    # Greenlandic (Kalaallisut) -> Danish
    # Google Translate does not support "kl", but Danish ("da") is widely used.
    "kl": "da",
    "fy": "nl",   # Frisian -> Dutch
    "lb": "de",   # Luxembourgish -> German
}

UNSUPPORTED_FALLBACKS: Dict[str, str] = {
    "hy": "ru",
    "is": "en",
    "ka": "ru",
    "kk": "ru",
    "km": "th",
    "lo": "th",
    "mg": "fr",
    "mk": "ru",
    "mn": "ru",
    "mt": "it",
    "my": "th",
    "ne": "en",
    "rw": "fr",
    "si": "en",
    "so": "en",
    "sr": "ru",
    "tg": "ru",
    "ti": "en",
    "tk": "tr",
    "to": "en",
    "uz": "ru",
}

ALL_FALLBACKS: Dict[str, str] = {
    **LANGUAGE_FALLBACKS,
    **UNSUPPORTED_FALLBACKS,
}


@dataclass(frozen=True)
class LocaleInfo:
    filename: str    # e.g. "ru_RU.json"
    locale: str      # e.g. "ru_RU"
    language: str    # e.g. "ru"
    region: str | None  # e.g. "RU" or None


def parse_locale_from_filename(filename: str) -> LocaleInfo:
    """Parse a filename like 'ru_RU.json' into a LocaleInfo."""
    name = filename
    if name.endswith(".json"):
        name = name[:-5]

    parts = name.split("_", 1)
    lang = parts[0]
    region = parts[1] if len(parts) == 2 else None

    return LocaleInfo(
        filename=filename,
        locale=name,
        language=lang,
        region=region,
    )


def _apply_custom_mappings(language: str, supported: Set[str]) -> str | None:
    """
    Apply small hand-tuned mappings on top of fallbacks.
    This is where we handle things like zh -> zh-Hans, etc.
    """
    # Chinese: your LibreTranslate reports "zh-Hans"
    if language == "zh":
        if "zh-Hans" in supported:
            return "zh-Hans"

    # Norwegian Bokmål: often "nb"
    if language == "no" and "nb" in supported:
        return "nb"

    return None


def resolve_target_lang(
    locale_info: LocaleInfo,
    supported: Set[str],
) -> str | None:
    """
    Resolve the best LibreTranslate language code for a given locale.

    1. Take primary language (e.g. 'ru' from 'ru_RU').
    2. Apply your fallback mappings (ALL_FALLBACKS).
    3. Apply custom mappings (e.g. zh -> zh-Hans).
    4. If final code is supported, return it; else None.
    """
    lang = locale_info.language

    # Step 1: fallback for unsupported languages
    if lang in ALL_FALLBACKS:
        lang = ALL_FALLBACKS[lang]

    # Step 2: custom per-language tweaks
    custom = _apply_custom_mappings(lang, supported)
    if custom is not None:
        lang = custom

    # Step 3: if still unsupported, give up
    if lang not in supported:
        return None

    return lang
