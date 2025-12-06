#!/usr/bin/env python3
"""
Fix suspicious (mostly-English) locales by copying translations from a
regionally plausible non-English fallback locale.

This is deliberately opinionated and uses a hard-coded map of:
    target_locale -> fallback_locale

Run from the project root:
    python fix_suspicious_with_regional_fallbacks.py
"""

import json
import os
from copy import deepcopy

TRANSLATIONS_DIR = os.path.join("localization", "translations")
KEY_REFERENCE_FILE = os.path.join(TRANSLATIONS_DIR, "key_reference.json")
THRESHOLD = 0.9  # "mostly English" cutoff

# Hard-coded regional fallbacks: target -> donor
REGIONAL_FALLBACKS = {
    "hy_AM": "ru_RU",  # Armenia -> Russian widely understood
    "is_IS": "da_DK",  # Iceland -> Nordic fallback
    "ne_NP": "hi_IN",  # Nepal -> Hindi (regional)
    "si_LK": "hi_IN",  # Sri Lanka -> Hindi (regional)
    "so_SO": "ar_AE",  # Somalia -> Arabic
    "ti_ER": "am_ET",  # Eritrea -> Amharic (Ethiopia)
    "tk_TM": "ru_RU",  # Turkmenistan -> Russian
    "to_TO": "fr_FR",  # Tonga -> generic non-English

    "ka_GE": "ru_RU",  # Georgia -> Russian
    "kk_KZ": "ru_RU",  # Kazakhstan -> Russian
    "km_KH": "th_TH",  # Cambodia -> Thai (regional)
    "ky_KG": "ru_RU",  # Kyrgyzstan -> Russian
    "lo_LA": "th_TH",  # Laos -> Thai
    "mg_MG": "fr_FR",  # Madagascar -> French
    "mk_MK": "hr_HR",  # North Macedonia -> South Slavic
    "mn_MN": "ru_RU",  # Mongolia -> Russian
    "ms_BN": "id_ID",  # Brunei -> Indonesian/Malay
    "ms_MY": "id_ID",  # Malaysia -> Indonesian/Malay
    "mt_MT": "it_IT",  # Malta -> Italian
    "my_MM": "th_TH",  # Myanmar -> Thai
    "rw_RW": "fr_FR",  # Rwanda -> French
    "sq_AL": "hr_HR",  # Albania -> South Slavic fallback
    "sr_ME": "hr_HR",  # Montenegro -> South Slavic
    "sr_RS": "hr_HR",  # Serbia -> South Slavic
    "tg_TJ": "ru_RU",  # Tajikistan -> Russian
    "ur_PK": "hi_IN",  # Pakistan -> Hindi (regional)
    "uz_UZ": "ru_RU",  # Uzbekistan -> Russian
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_english_fraction(locale_data, reference):
    same = 0
    total = 0
    for k, v_en in reference.items():
        if k in locale_data:
            total += 1
            if locale_data[k] == v_en:
                same += 1
    frac = same / total if total else 0.0
    return same, total, frac


def main():
    if not os.path.isdir(TRANSLATIONS_DIR):
        print(f"ERROR: translations dir not found: {TRANSLATIONS_DIR}")
        return

    if not os.path.isfile(KEY_REFERENCE_FILE):
        print(f"ERROR: key_reference.json not found at: {KEY_REFERENCE_FILE}")
        return

    reference = load_json(KEY_REFERENCE_FILE)

    # Load all locales
    locales = {}
    stats = {}
    for fname in sorted(os.listdir(TRANSLATIONS_DIR)):
        if not fname.endswith(".json"):
            continue
        if fname == "key_reference.json":
            continue
        if fname.endswith(".json.done"):
            continue

        loc = fname[:-5]
        path = os.path.join(TRANSLATIONS_DIR, fname)
        data = load_json(path)
        locales[loc] = data

        same, total, frac = compute_english_fraction(data, reference)
        stats[loc] = (same, total, frac)

    # Suspicious = mostly English and not an English locale
    suspicious = {
        loc: frac
        for loc, (same, total, frac) in stats.items()
        if not loc.startswith("en_") and frac >= THRESHOLD
    }

    print("=== Suspicious (mostly-English) locales BEFORE fix ===")
    if not suspicious:
        print("None.")
    else:
        for loc, frac in sorted(suspicious.items(), key=lambda kv: kv[1], reverse=True):
            print(f"{loc:7s}  frac={frac:0.2f}")

    changed = []
    skipped = []

    for target, frac in suspicious.items():
        donor = REGIONAL_FALLBACKS.get(target)
        if not donor:
            skipped.append((target, frac, "no regional fallback mapping defined"))
            continue

        if donor not in locales:
            skipped.append((target, frac, f"fallback {donor} JSON not found"))
            continue

        # Overwrite target with donor content
        locales[target] = deepcopy(locales[donor])
        changed.append((target, frac, donor))

    # Write back changed files
    for target, frac, donor in changed:
        path = os.path.join(TRANSLATIONS_DIR, target + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(locales[target], f, ensure_ascii=False, indent=4)

    print("\n=== Summary of changes ===")
    if changed:
        for target, frac, donor in sorted(changed, key=lambda x: x[0]):
            print(
                f"{target:7s} (was {frac:0.2f} English-like) "
                f"-> now copied from {donor}"
            )
    else:
        print("No locales were changed.")

    if skipped:
        print("\n=== Suspicious locales skipped (no fix applied) ===")
        for loc, frac, reason in sorted(skipped, key=lambda x: x[0]):
            print(f"{loc:7s}  frac={frac:0.2f}  reason: {reason}")


if __name__ == "__main__":
    main()
