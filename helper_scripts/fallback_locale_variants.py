#!/usr/bin/env python3
import json
import os
from copy import deepcopy

BASE = os.path.join("localization", "translations")
KEY_REF_FILE = os.path.join(BASE, "key_reference.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def english_fraction(data, ref):
    same = total = 0
    for k, v_en in ref.items():
        if k in data:
            total += 1
            if data[k] == v_en:
                same += 1
    return (same, total, same / total if total else 0.0)


def main():
    # 1) Load English reference
    key_ref = load_json(KEY_REF_FILE)

    # 2) Load all locale files
    locales = {}
    fractions = {}
    for fname in os.listdir(BASE):
        if not fname.endswith(".json"):
            continue
        if fname == "key_reference.json":
            continue

        loc = fname[:-5]
        path = os.path.join(BASE, fname)
        data = load_json(path)
        locales[loc] = data

        same, total, frac = english_fraction(data, key_ref)
        fractions[loc] = (same, total, frac)

    # 3) For each language prefix (pt, es, nl, etc.), pick a canonical locale
    #    that is NOT mostly English (fraction < 0.9).
    from collections import defaultdict

    langs = defaultdict(list)
    for loc, (same, total, frac) in fractions.items():
        lang = loc.split("_")[0]
        langs[lang].append((loc, frac))

    canonical = {}
    for lang, entries in langs.items():
        best = None
        for loc, frac in entries:
            if loc.startswith("en_"):
                continue
            if frac >= 0.9:
                continue  # mostly English, skip as canon
            if best is None or frac < best[1]:
                best = (loc, frac)
        if best:
            canonical[lang] = best  # (locale_code, frac)

    print("Canonical bases per language (used as donors):")
    for lang, (loc, frac) in sorted(canonical.items()):
        print(f"  {lang}: {loc} (English fraction={frac:.2f})")

    # 4) Apply fallback for locales that are basically English but have a canon
    changed = []
    for loc, data in locales.items():
        lang = loc.split("_")[0]
        same, total, frac = fractions[loc]

        if frac >= 0.9 and not loc.startswith("en_") and lang in canonical:
            base_loc, _ = canonical[lang]
            if base_loc == loc:
                continue  # don't overwrite the canonical itself

            print(
                f"Using {base_loc} as fallback for {loc} (English fraction={frac:.2f})"
            )
            base_data = locales[base_loc]

            # Shallow copy of the base translations
            new_data = deepcopy(base_data)

            # If you want to preserve any locale-specific keys (e.g. digits),
            # you can do it here. For now we just use the base data as-is.
            locales[loc] = new_data
            changed.append(loc)

    # 5) Write back only the changed locale files
    for loc in changed:
        path = os.path.join(BASE, loc + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(locales[loc], f, ensure_ascii=False, indent=4)

    if changed:
        print("\nUpdated locales:")
        for loc in sorted(changed):
            print("  -", loc)
    else:
        print("\nNo locales needed fallback updates.")


if __name__ == "__main__":
    main()
