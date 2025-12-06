#!/usr/bin/env python3
"""
Fix digit sets for specific locales:

- ur_PK: use Arabic-Indic digits (same as Arabic/Persian).
- km_KH: Khmer digits.
- lo_LA: Lao digits.
- my_MM: Burmese digits.

Run from the project root:

    python fix_specific_digits.py
"""

import json
import os

TRANSLATIONS_DIR = os.path.join("localization", "translations")

DIGIT_SETS = {
    # Arabic-Indic digits for Urdu (Pakistan)
    "ur_PK": ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"],

    # Khmer digits for Cambodia
    "km_KH": ["០", "១", "២", "៣", "៤", "៥", "៦", "៧", "៨", "៩"],

    # Lao digits for Laos
    "lo_LA": ["໐", "໑", "໒", "໓", "໔", "໕", "໖", "໗", "໘", "໙"],

    # Burmese digits for Myanmar
    "my_MM": ["၀", "၁", "၂", "၃", "၄", "၅", "၆", "၇", "၈", "၉"],
}


def main():
    if not os.path.isdir(TRANSLATIONS_DIR):
        print("ERROR: translations dir not found at", TRANSLATIONS_DIR)
        return

    changed = []

    for locale_code, digits in DIGIT_SETS.items():
        fname = f"{locale_code}.json"
        path = os.path.join(TRANSLATIONS_DIR, fname)

        if not os.path.isfile(path):
            print(f"{fname}: file not found, skipping.")
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        old_digits = data.get("digits")
        data["digits"] = digits

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        changed.append((locale_code, old_digits, digits))

    print("\nUpdated digit maps:")
    if not changed:
        print("  (none)")
    else:
        for loc, old, new in changed:
            print(f"  {loc}: {old!r} -> {''.join(new)}")


if __name__ == "__main__":
    main()
