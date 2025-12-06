#!/usr/bin/env python3
"""
Scan localization/translations/*.json for locales that are basically English,
report them, and auto-fix them by copying from a better base locale that shares
the same language code (e.g. pt_BR -> pt_AO, zh_CN -> zh_HK).

"Incorrect" here means:
- Locale is NOT an English locale (not starting with "en_"), AND
- At least THRESHOLD (default 0.9) of keys are identical to key_reference.json.

For each language (xx part of xx_YY), we choose a canonical "base" locale:
- A locale of the same language whose strings are mostly NOT English
  (English fraction < THRESHOLD), and with the lowest English fraction.

Suspicious locales for that language will have their entire JSON replaced with
a copy of the base locale's JSON.

The script prints:
- A full report of locales and their "English fraction".
- A summary of which files were changed and which could not be fixed.
"""

import json
import os
from collections import defaultdict
from copy import deepcopy

# Configuration
TRANSLATIONS_DIR = os.path.join("localization", "translations")
KEY_REFERENCE_FILE = os.path.join(TRANSLATIONS_DIR, "key_reference.json")

# Consider a locale "likely incorrect" if this fraction or higher of keys
# are identical to the English reference.
THRESHOLD = 0.9


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_english_fraction(locale_data, reference):
    """Return (same_count, total_count, fraction_same_as_english)."""
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

    # 1) Load all locale JSONs and compute "English fraction"
    locale_data = {}
    english_stats = {}

    for fname in sorted(os.listdir(TRANSLATIONS_DIR)):
        if not fname.endswith(".json"):
            continue
        if fname == "key_reference.json":
            continue
        # ignore helper marker files like *.json.done if they exist
        if fname.endswith(".json.done"):
            continue

        loc = fname[:-5]  # strip ".json"
        path = os.path.join(TRANSLATIONS_DIR, fname)

        data = load_json(path)
        locale_data[loc] = data

        same, total, frac = compute_english_fraction(data, reference)
        english_stats[loc] = (same, total, frac)

    # 2) Print a sorted report of all locales
    print("=== Locale English-likeness report (fraction of keys equal to English) ===")
    for loc, (same, total, frac) in sorted(
        english_stats.items(), key=lambda kv: kv[1][2], reverse=True
    ):
        print(f"{loc:7s}  same={same:2d}/{total:2d}  frac={frac:0.2f}")

    # 3) Group locales by language (xx in xx_YY)
    by_lang = defaultdict(list)
    for loc, (same, total, frac) in english_stats.items():
        lang = loc.split("_")[0]
        by_lang[lang].append((loc, frac))

    # 4) Choose a canonical non-English base locale for each language
    canonical_base = {}  # lang -> (base_locale, frac)
    for lang, entries in by_lang.items():
        best = None
        for loc, frac in entries:
            # We never use English locales as bases (they're always 1.0)
            if loc.startswith("en_"):
                continue
            # Only consider candidates that are not "mostly English"
            if frac >= THRESHOLD:
                continue
            if best is None or frac < best[1]:
                best = (loc, frac)
        if best:
            canonical_base[lang] = best

    print("\n=== Canonical non-English bases per language (used as donors) ===")
    if canonical_base:
        for lang, (loc, frac) in sorted(canonical_base.items()):
            print(f"{lang:2s} -> {loc} (English fraction={frac:0.2f})")
    else:
        print("No non-English bases found; nothing to do.")
        return

    # 5) Identify suspicious (likely incorrect) locales and fix them where possible
    suspicious = []  # (loc, frac)
    for loc, (same, total, frac) in english_stats.items():
        if loc.startswith("en_"):
            continue  # English locales are expected to be English
        if frac >= THRESHOLD:
            suspicious.append((loc, frac))

    print("\n=== Suspicious locales (likely incorrect: mostly English) ===")
    if not suspicious:
        print("None.")
    else:
        for loc, frac in sorted(suspicious, key=lambda kv: kv[1], reverse=True):
            print(f"{loc:7s}  frac={frac:0.2f}")

    # 6) Apply fixes: copy from canonical base if available for that language
    changed = []
    not_fixed = []

    for loc, frac in suspicious:
        lang = loc.split("_")[0]
        if lang not in canonical_base:
            not_fixed.append((loc, frac, "no non-English base for this language"))
            continue

        base_loc, base_frac = canonical_base[lang]
        if base_loc == loc:
            # This would mean the canonical is itself flagged as suspicious
            not_fixed.append((loc, frac, "canonical locale itself is suspicious"))
            continue

        # Replace this locale's data with a copy of the base locale data
        locale_data[loc] = deepcopy(locale_data[base_loc])
        changed.append((loc, frac, base_loc, base_frac))

    # 7) Write back changed locale files
    for loc, frac, base_loc, base_frac in changed:
        path = os.path.join(TRANSLATIONS_DIR, loc + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(locale_data[loc], f, ensure_ascii=False, indent=4)

    # 8) Summary
    print("\n=== Summary of fixes applied ===")
    if changed:
        for loc, frac, base_loc, base_frac in sorted(changed, key=lambda x: x[0]):
            print(
                f"{loc:7s} (was {frac:0.2f} English) "
                f"-> copied from {base_loc} (English fraction={base_frac:0.2f})"
            )
    else:
        print("No files changed (no suspicious locales with suitable base).")

    if not_fixed:
        print("\n=== Suspicious locales that could NOT be fixed automatically ===")
        for loc, frac, reason in sorted(not_fixed, key=lambda x: x[0]):
            print(f"{loc:7s}  frac={frac:0.2f}  reason: {reason}")


if __name__ == "__main__":
    main()
