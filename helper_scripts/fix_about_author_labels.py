#!/usr/bin/env python3
"""
Fix up 'author'-related labels after the previous mis-step.

- For ALL locales except ru_RU:
    * If there is an 'author' key with value 'Author', delete it
      (revert the earlier script that added English everywhere).

- For ru_RU:
    * Ensure 'author' is set to a proper Russian label 'Автор'.
    * For every key whose name contains 'author' (case-insensitive)
      and whose value is '.' or '', set it to 'Автор' as well.

This should:
- Remove unwanted English 'Author' keys from non-English locales.
- Fix the about-dialog label for Asia/Almaty (ru_RU) where you currently
  see ". Oliver Ernster" instead of a real word.

Run from the project root:

    python fix_about_author_labels.py
"""

import json
import os

TRANSLATIONS_DIR = os.path.join("localization", "translations")

def main():
    if not os.path.isdir(TRANSLATIONS_DIR):
        print("ERROR: translations dir not found at", TRANSLATIONS_DIR)
        return

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

        original = dict(data)  # shallow copy for comparison

        # 1) For all locales except ru_RU: revert 'author': 'Author'
        if loc != "ru_RU":
            if "author" in data and data["author"] == "Author":
                del data["author"]

        # 2) For ru_RU: enforce proper Russian label(s)
        if loc == "ru_RU":
            # Ensure plain 'author' exists and is Russian
            if data.get("author") in (None, "", ".", "Author"):
                data["author"] = "Автор"

            # Fix any other *author*-related keys that have '.' or empty
            for key, value in list(data.items()):
                if "author" in key.lower() and value in (".", "", None):
                    data[key] = "Автор"

        if data != original:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            changed.append(loc)

    if not changed:
        print("No changes were necessary.")
    else:
        print("Updated locales:")
        for loc in changed:
            print("  ", loc)


if __name__ == "__main__":
    main()
