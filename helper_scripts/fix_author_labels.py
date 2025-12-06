#!/usr/bin/env python3
"""
Fix the 'author' label in localization/translations/*.json.

- For ru_RU: force a proper Russian label "Автор".
- For all other locales: if the 'author' key is missing OR has a value
  of "." or "", set it to the English default from key_reference.json
  (or "Author" as a last resort).

Run from the project root:

    python fix_author_labels.py
"""

import json
import os

TRANSLATIONS_DIR = os.path.join("localization", "translations")
KEY_REF_FILE = os.path.join(TRANSLATIONS_DIR, "key_reference.json")

AUTHOR_KEY = "author"  # adjust if your key is named differently


def main():
    if not os.path.isdir(TRANSLATIONS_DIR):
        print("ERROR: translations dir not found at", TRANSLATIONS_DIR)
        return

    if not os.path.isfile(KEY_REF_FILE):
        print("ERROR: key_reference.json not found at", KEY_REF_FILE)
        return

    with open(KEY_REF_FILE, "r", encoding="utf-8") as f:
        key_ref = json.load(f)

    english_default = key_ref.get(AUTHOR_KEY, "Author")

    changed = []

    for fname in sorted(os.listdir(TRANSLATIONS_DIR)):
        if not fname.endswith(".json"):
            continue
        if fname == "key_reference.json":
            continue

        loc = fname[:-5]
        path = os.path.join(TRANSLATIONS_DIR, fname)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        old_val = data.get(AUTHOR_KEY)

        # 1) ru_RU → force proper Russian
        if loc == "ru_RU":
            new_val = "Автор"
        else:
            # 2) other locales:
            #    – if missing / "." / "" → fall back to English "Author"
            if old_val in (None, "", "."):
                new_val = english_default
            else:
                new_val = old_val

        if new_val != old_val:
            data[AUTHOR_KEY] = new_val
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            changed.append((loc, old_val, new_val))

    print("Updated author labels:")
    if not changed:
        print("  (no changes needed)")
    else:
        for loc, old, new in changed:
            print(f"  {loc}: {old!r} -> {new!r}")


if __name__ == "__main__":
    main()
