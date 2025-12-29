#!/usr/bin/env python3
"""
Automatically fix timezone_locale_map.json by adding locale mappings
for ALL timezones that currently fall back to en_US.

- Preserves existing mappings.
- Adds mappings for every pytz.common_timezones entry that is not yet
  in timezone_locale_map.json.
- Uses a country-code -> locale mapping (REGION_DEFAULT_LANGUAGE).
- Only uses locale codes that actually have a translation JSON file.
- Falls back to en_GB (or en_US if en_GB is unavailable) when we have
  no better guess.

Run from the project root:

    python auto_map_all_timezones.py
"""

import json
import os
from collections import defaultdict

import pytz

MAP_PATH = "timezone_locale_map.json"
TRANSLATIONS_DIR = os.path.join("localization", "translations")


# ---------------------------------------------------------------------
# 1. Language mapping table (country code -> locale code)
# ---------------------------------------------------------------------
# NOTE: These are "best effort" defaults. They will only be used if the
# corresponding locale JSON file actually exists in TRANSLATIONS_DIR.

REGION_DEFAULT_LANGUAGE = {
    # South America
    "AR": "es_AR",
    "CL": "es_CL",
    "BO": "es_BO",
    "PY": "es_PY",
    "UY": "es_UY",
    "PE": "es_PE",
    "CO": "es_CO",
    "VE": "es_VE",
    "EC": "es_EC",
    "GF": "fr_FR",
    "BR": "pt_BR",
    # Central America / Caribbean / North LatAm
    "MX": "es_MX",
    "CR": "es_CR",
    "PA": "es_PA",
    "GT": "es_GT",
    "NI": "es_NI",
    "SV": "es_SV",
    "HN": "es_HN",
    "DO": "es_DO",
    "PR": "es_PR",
    "CU": "es_CU",
    "BZ": "en_GB",  # Belize - English
    # Europe (subset – enough to cover your remaining tzs)
    "ES": "es_ES",
    "PT": "pt_PT",
    "FR": "fr_FR",
    "DE": "de_DE",
    "IT": "it_IT",
    "GB": "en_GB",
    "NL": "nl_NL",
    "BE": "fr_FR",  # safe fallback
    "CH": "de_CH",
    "NO": "nb_NO",
    "SE": "sv_SE",
    "FI": "fi_FI",
    "DK": "da_DK",
    "PL": "pl_PL",
    "RO": "ro_RO",
    "UA": "uk_UA",
    "RU": "ru_RU",
    # Africa (subset)
    "ZA": "en_ZA",
    "NG": "en_GB",
    "KE": "en_GB",
    "ZW": "en_GB",
    "GH": "en_GB",
    "MZ": "pt_MZ",
    "AO": "pt_AO",
    "CD": "fr_CD",
    "MG": "fr_FR",
    "MA": "ar_MA",
    "EH": "ar_MA",  # Western Sahara (El_Aaiun etc)
    # Middle East / South / East Asia
    "AE": "ar_AE",
    "SA": "ar_SA",
    "IQ": "ar_IQ",
    "IR": "fa_IR",
    "AF": "fa_AF",
    "PK": "ur_PK",
    "IN": "hi_IN",
    "NP": "ne_NP",
    "BD": "bn_BD",
    "KH": "km_KH",
    "LA": "lo_LA",
    "MM": "my_MM",
    "TH": "th_TH",
    "JP": "ja_JP",
    "CN": "zh_CN",
    "TW": "zh_TW",
    "HK": "zh_HK",
    "SG": "en_GB",
    # Oceania
    "AU": "en_AU",
    "NZ": "en_GB",
    "FJ": "en_GB",
    "PF": "fr_FR",
    # Antarctica
    "AQ": "en_GB",
}

# ---------------------------------------------------------------------
# 2. Build tz -> country-code reverse mapping from pytz
# ---------------------------------------------------------------------


def build_tz_to_country() -> dict:
    tz_to_cc = defaultdict(list)
    for cc, tzs in pytz.country_timezones.items():
        for tz in tzs:
            tz_to_cc[tz].append(cc)
    return tz_to_cc


TZ_TO_COUNTRY = build_tz_to_country()


def derive_cc_from_timezone(tz: str):
    """
    Try to determine a country code for this timezone.

    Strategy:
      1. If tz appears in TZ_TO_COUNTRY, use that country (first entry).
      2. If tz starts with US/ or Canada/, map to US/CA.
      3. Antarctica -> AQ.
      4. Otherwise, None (we'll fall back to English).
    """
    if tz in TZ_TO_COUNTRY:
        return TZ_TO_COUNTRY[tz][0]

    if tz.startswith("US/"):
        return "US"
    if tz.startswith("Canada/"):
        return "CA"

    if tz.startswith("Antarctica/"):
        return "AQ"

    # GMT, UTC, etc → no specific country
    return None


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------


def main():
    if not os.path.isfile(MAP_PATH):
        print("ERROR: timezone_locale_map.json not found at", MAP_PATH)
        return

    if not os.path.isdir(TRANSLATIONS_DIR):
        print("ERROR: translations dir not found at", TRANSLATIONS_DIR)
        return

    # Existing mappings
    with open(MAP_PATH, "r", encoding="utf-8") as f:
        tz_map = json.load(f)

    # Available locale JSONs
    existing_locales = {
        fname[:-5]
        for fname in os.listdir(TRANSLATIONS_DIR)
        if fname.endswith(".json") and fname != "key_reference.json"
    }

    # Choose default English fallback
    english_fallback = (
        "en_GB"
        if "en_GB" in existing_locales
        else ("en_US" if "en_US" in existing_locales else None)
    )
    if not english_fallback:
        print("ERROR: No en_GB or en_US translation found; aborting.")
        return

    all_tzs = sorted(pytz.common_timezones)

    added = []

    for tz in all_tzs:
        if tz in tz_map:
            continue  # already mapped

        cc = derive_cc_from_timezone(tz)

        loc = None
        if cc and cc in REGION_DEFAULT_LANGUAGE:
            candidate = REGION_DEFAULT_LANGUAGE[cc]
            if candidate in existing_locales:
                loc = candidate

        if loc is None:
            # Either no country, or no suitable locale file → fall back
            loc = english_fallback

        tz_map[tz] = loc
        added.append((tz, loc))

    # Write back
    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(tz_map, f, ensure_ascii=False, indent=4)

    print(f"Added {len(added)} new timezone→locale mappings.")
    print("Examples:")
    for tz, loc in added[:20]:
        print(f"  {tz:35s} -> {loc}")


if __name__ == "__main__":
    main()
