"""Structural tests over the shipped locale files.

The localisation manager resolves a key against the requested locale, then
English, then the key itself. That fallback is right at runtime, because a
user should never see a raw key. It also means a locale can quietly ship the
English string and nothing anywhere says so: the value is present, so it is
used exactly as written however wrong it is.

That is not hypothetical. A bulk key-adding script once carried a table of
fifty-one languages against a corpus of seventy-one and filled English for the
remainder, leaving twenty languages showing "Credits: (Media)" for years with
no symptom. These tests make that state fail instead of pass.

They read the JSON files directly and import nothing from the application.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRANSLATIONS_DIR = PROJECT_ROOT / "localization" / "translations"

# The locale every other locale falls back to.
REFERENCE_LOCALE = "en_GB"
# Not a locale: the key listing kept beside the translations.
REFERENCE_FILE = "key_reference.json"

# Keys whose English value is correct in any language, so an identical value
# proves nothing. Proper nouns, an internationally recognised acknowledgement,
# symbol-like abbreviations and the digit table. Date names are here for a
# different reason: three-letter month and day abbreviations coincide across
# most European languages by design, so equality cannot distinguish a real
# translation from a missing one and this test must not pretend otherwise.
_DATE_KEYS = frozenset(
    [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
) | frozenset(
    f"calendar.days.{day}"
    for day in (
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )
)

ENGLISH_BY_DESIGN = (
    frozenset(
        [
            "digits",
            "author_name",
            "app_name",
            "ok",
            "minutes_suffix",
            "hours_suffix",
            "sound_marimba",
        ]
    )
    | _DATE_KEYS
)

# Keys that a named locale legitimately writes exactly as English: a loanword,
# a shared spelling or a word the language has adopted whole. Every entry is a
# claim about one language, so each is listed rather than waved through by key.
#
# This list may only ever shrink. A new locale showing an English value is a
# failure, not an addition. test_accepted_english_is_still_english fails
# when an entry here has since been translated, so a stale exemption cannot
# outlive the value it excused.
ACCEPTED_ENGLISH: dict[str, frozenset[str]] = {
    # "Licence" is also the French, Czech and Latvian spelling.
    "license": frozenset(
        [
            "cs_CZ",
            "fr_BF",
            "fr_BI",
            "fr_BJ",
            "fr_BL",
            "fr_CA",
            "fr_CD",
            "fr_CF",
            "fr_CG",
            "fr_CI",
            "fr_CM",
            "fr_DJ",
            "fr_FR",
            "fr_GA",
            "fr_GF",
            "fr_GN",
            "fr_GP",
            "fr_HT",
            "fr_KM",
            "fr_LU",
            "fr_MC",
            "fr_MF",
            "fr_ML",
            "fr_MQ",
            "fr_NC",
            "fr_NE",
            "fr_PF",
            "fr_PM",
            "fr_RE",
            "fr_SN",
            "fr_TD",
            "fr_TG",
            "fr_WF",
            "fr_YT",
            "lv_LV",
        ]
    ),
    # Same word as the licence menu entry above.
    "license_dialog_title": frozenset(
        [
            "cs_CZ",
            "fr_BF",
            "fr_BI",
            "fr_BJ",
            "fr_BL",
            "fr_CA",
            "fr_CD",
            "fr_CF",
            "fr_CG",
            "fr_CI",
            "fr_CM",
            "fr_DJ",
            "fr_FR",
            "fr_GA",
            "fr_GF",
            "fr_GN",
            "fr_GP",
            "fr_HT",
            "fr_KM",
            "fr_LU",
            "fr_MC",
            "fr_MF",
            "fr_ML",
            "fr_MQ",
            "fr_NC",
            "fr_NE",
            "fr_PF",
            "fr_PM",
            "fr_RE",
            "fr_SN",
            "fr_TD",
            "fr_TG",
            "fr_WF",
            "fr_YT",
            "lv_LV",
        ]
    ),
    # "Version" is written identically in German, Danish, Swedish,
    # Icelandic and Greenlandic.
    "version": frozenset(
        [
            "da_DK",
            "de_AT",
            "de_CH",
            "de_DE",
            "de_LI",
            "is_IS",
            "kl_GL",
            "sv_AX",
            "sv_SE",
        ]
    ),
    # Dutch uses the English "Website".
    "website": frozenset(["nl_AW", "nl_BE", "nl_CW", "nl_NL", "nl_SR", "nl_SX"]),
    # "Alarm" is the word itself in these languages.
    "alarm_ringing_title": frozenset(
        [
            "bs_BA",
            "da_DK",
            "hr_HR",
            "id_ID",
            "nb_NO",
            "pl_PL",
            "sq_AL",
            "sv_AX",
            "sv_SE",
            "tr_TR",
        ]
    ),
    # "Spiral" is the word in the Nordic languages and a loanword
    # in the others.
    "skin_spiral": frozenset(
        ["az_AZ", "da_DK", "id_ID", "nb_NO", "sv_AX", "sv_SE", "tk_TM", "uz_UZ"]
    ),
    # Malay, Turkmen and Uzbek use the English "Import".
    "alarm_import": frozenset(["ms_BN", "ms_MY", "tk_TM", "uz_UZ"]),
    # Indonesian uses "Edit" as its own verb.
    "alarm_edit": frozenset(["id_ID"]),
    # Same verb as the entry above.
    "alarm_editor_title_edit": frozenset(["id_ID"]),
}


def _load(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def _locale_files() -> list[Path]:
    """Return every shipped locale file, newest reference file excluded."""
    return sorted(
        path for path in TRANSLATIONS_DIR.glob("*.json") if path.name != REFERENCE_FILE
    )


def _reference() -> dict[str, object]:
    return _load(TRANSLATIONS_DIR / f"{REFERENCE_LOCALE}.json")


def _non_english_files() -> list[Path]:
    return [path for path in _locale_files() if not path.stem.startswith("en_")]


def test_every_locale_carries_every_reference_key() -> None:
    """No locale relies on the English fallback for a missing key."""
    reference = _reference()
    assert reference, "the reference locale is empty or unreadable"
    for path in _locale_files():
        missing = sorted(key for key in reference if key not in _load(path))
        assert not missing, (
            f"{path.name} is missing {len(missing)} key(s) and would fall back "
            f"to {REFERENCE_LOCALE}: {missing[:5]}"
        )


def test_no_locale_silently_ships_the_english_value() -> None:
    """A non-English locale never repeats the English string unaccounted for.

    A value equal to English is either listed in ENGLISH_BY_DESIGN, where the
    English form is correct in any language, else named in ACCEPTED_ENGLISH for
    that specific locale. Anything else is an untranslated string that the
    fallback would otherwise hide.
    """
    reference = _reference()
    offenders: list[str] = []
    for path in _non_english_files():
        data = _load(path)
        for key, english in reference.items():
            if key in ENGLISH_BY_DESIGN:
                continue
            if path.stem in ACCEPTED_ENGLISH.get(key, frozenset()):
                continue
            if data.get(key) == english:
                offenders.append(f"{path.stem}:{key} = {english!r}")
    assert not offenders, (
        f"{len(offenders)} untranslated value(s) carrying the English string: "
        f"{offenders[:10]}"
    )


def test_accepted_english_is_still_english() -> None:
    """Every ACCEPTED_ENGLISH entry still describes a real value.

    Without this the exemption list would only ever grow; an entry could then
    outlive the value it excused. Translating one of these should require
    deleting its entry here, so the list can only shrink.
    """
    reference = _reference()
    stale: list[str] = []
    for key, locales in ACCEPTED_ENGLISH.items():
        assert key in reference, f"ACCEPTED_ENGLISH names an unknown key: {key}"
        for locale in sorted(locales):
            path = TRANSLATIONS_DIR / f"{locale}.json"
            assert path.is_file(), f"ACCEPTED_ENGLISH names a missing locale: {locale}"
            if _load(path).get(key) != reference[key]:
                stale.append(f"{locale}:{key}")
    assert not stale, (
        f"{len(stale)} stale exemption(s): these are translated now, so remove "
        f"them from ACCEPTED_ENGLISH: {stale}"
    )
