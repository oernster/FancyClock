#!/usr/bin/env python3
"""
Fix single-dot placeholder translations in *all* locale JSONs.

- Only modifies keys whose value is literally "." (with optional whitespace).
- For Russian-ish locales (ru_RU, kk_KZ, ka_GE, ky_KG, mn_MN, tg_TJ,
  uz_UZ, hy_AM, tk_TM), it copies the value from ru_RU.json for that key
  if available. This keeps those regions consistent with Russian.

- For all other locales:
    * If key_reference.json has a value for this key, use that
      (English fallback is better than a bare dot).
    * Otherwise, we replace "." with an empty string "" to avoid
      showing a lone dot in the UI.

This should fix things like the About dialog line showing
". Oliver Ernster" for Asia/Almaty and similar timezones.

Run from the project root:

    python fix_single_dot_placeholders.py
"""

import json
import os

TRANSLATIONS_DIR = os.path.join("localization", "translations")
KEY_REF_FILE = os.path.join(TRANSLATIONS_DIR, "key_reference.json")
RU_FILE = os.path.join(TRANSLATIONS_DIR, "ru_RU.json")

# Locales that we treat as "Russian cluster" and want to align with ru_RU
RUSSIAN_CLUSTER = {
    "ru_RU",
    "kk_KZ",  # Kazakhstan
    "ka_GE",  # Georgia (you previously copied from ru_RU)
    "ky_KG",  # Kyrgyzstan
    "mn_MN",  # Mongolia
    "tg_TJ",  # Tajikistan
    "uz_UZ",  # Uzbekistan
    "hy_AM",  # Armenia
    "tk_TM",  # Turkmenistan
}


def is_single_dot(value: str) -> bool:
    """Return True if value is literally '.' with optional surrounding whitespace."""
    if not isinstance(value, str):
        return False
    return value.strip() == "."


def main():
    if not os.path.isdir(TRANSLATIONS_DIR):
        print("ERROR: translations dir not found at", TRANSLATIONS_DIR)
        return

    if not os.path.isfile(KEY_REF_FILE):
        print("ERROR: key_reference.json not found at", KEY_REF_FILE)
        return

    if not os.path.isfile(RU_FILE):
        print("ERROR: ru_RU.json not found at", RU_FILE)
        return

    with open(KEY_REF_FILE, "r", encoding="utf-8") as f:
        key_ref = json.load(f)

    with open(RU_FILE, "r", encoding="utf-8") as f:
        ru_data = json.load(f)

    overall_changes = []

    for fname in sorted(os.listdir(TRANSLATIONS_DIR)):
        if not fname.endswith(".json"):
            continue
        if fname == "key_reference.json":
            continue

        loc = fname[:-5]
        path = os.path.join(TRANSLATIONS_DIR, fname)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        changed_this_file = []

        for key, value in list(data.items()):
            if not is_single_dot(value):
                continue

            if loc in RUSSIAN_CLUSTER and key in ru_data:
                # Use Russian value for Russian-ish locales
                new_val = ru_data[key]
            else:
                # Fallback: use English default if available
                if key in key_ref:
                    new_val = key_ref[key]
                else:
                    # Last resort: empty string instead of a dot
                    new_val = ""

            if new_val != value:
                data[key] = new_val
                changed_this_file.append((key, value, new_val))

        if changed_this_file:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            overall_changes.append((loc, changed_this_file))

    if not overall_changes:
        print("No '.' placeholders found in any locale; nothing changed.")
    else:
        print("Updated '.' placeholders in the following locales/keys:")
        for loc, changes in overall_changes:
            print(f"- {loc}:")
            for key, old, new in changes:
                print(f"    {key}: {old!r} -> {new!r}")


if __name__ == "__main__":
    main()
