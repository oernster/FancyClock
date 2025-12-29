#!/usr/bin/env python3
"""
Report timezones that currently fall back to en_US (because they aren't
in timezone_locale_map.json), and auto-add some obvious mappings.

- Writes a full list of fallback timezones to:
      timezones_falling_back_to_en_US.txt

- Automatically adds mappings for:
    * All America/Argentina/* -> es_AR
    * America/Araguaina      -> pt_BR

Run from the project root:

    python report_and_fix_timezones.py
"""

import json
import os

import pytz

MAP_PATH = "timezone_locale_map.json"
REPORT_PATH = "timezones_falling_back_to_en_US.txt"

# Obvious mappings we want to add if missing
AUTO_MAPPINGS = {
    # All Argentina zones -> es_AR
    "America/Argentina/Buenos_Aires": "es_AR",
    "America/Argentina/Catamarca": "es_AR",
    "America/Argentina/Cordoba": "es_AR",
    "America/Argentina/Jujuy": "es_AR",
    "America/Argentina/La_Rioja": "es_AR",
    "America/Argentina/Mendoza": "es_AR",
    "America/Argentina/Rio_Gallegos": "es_AR",
    "America/Argentina/Salta": "es_AR",
    "America/Argentina/San_Juan": "es_AR",
    "America/Argentina/San_Luis": "es_AR",
    "America/Argentina/Tucuman": "es_AR",
    "America/Argentina/Ushuaia": "es_AR",
    # Brazil: Araguaina -> Portuguese (Brazil)
    "America/Araguaina": "pt_BR",
}


def main():
    if not os.path.isfile(MAP_PATH):
        print("ERROR: timezone_locale_map.json not found at", MAP_PATH)
        return

    with open(MAP_PATH, "r", encoding="utf-8") as f:
        tz_map = json.load(f)

    # 1) Figure out which timezones the app shows (same as the dialog)
    all_tzs = sorted(pytz.common_timezones)

    # 2) Which ones fall back to en_US?  (i.e. not in the map at all)
    fallback_tzs = [tz for tz in all_tzs if tz not in tz_map]

    print(f"Found {len(all_tzs)} common timezones.")
    print(f"{len(tz_map)} timezones have explicit locale mappings.")
    print(f"{len(fallback_tzs)} timezones currently fall back to en_US.\n")

    # 3) Write the full fallback list to a text file for inspection
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        for tz in fallback_tzs:
            f.write(tz + "\n")

    print(f"Full list of fallback timezones written to: {REPORT_PATH}")
    print("First 20 fallbacks for a quick peek:")
    for tz in fallback_tzs[:20]:
        print("  ", tz)

    # 4) Auto-add obvious mappings where the timezone is currently falling back
    changed = []
    skipped_existing = []

    for tz, loc in AUTO_MAPPINGS.items():
        if tz in tz_map:
            if tz_map[tz] == loc:
                skipped_existing.append((tz, tz_map[tz], "already mapped correctly"))
            else:
                skipped_existing.append(
                    (tz, tz_map[tz], "already mapped to a different locale")
                )
            continue

        # Only add mappings for tzs that actually exist in pytz.common_timezones
        if tz not in all_tzs:
            skipped_existing.append((tz, None, "not in pytz.common_timezones"))
            continue

        tz_map[tz] = loc
        changed.append((tz, loc))

    # 5) Write back updated timezone_locale_map.json if we changed anything
    if changed:
        with open(MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(tz_map, f, ensure_ascii=False, indent=4)
        print("\nAdded/updated mappings:")
        for tz, loc in changed:
            print(f"  {tz:35s} -> {loc}")
    else:
        print("\nNo AUTO_MAPPINGS were applied (everything already present).")

    if skipped_existing:
        print("\nMappings we did NOT change:")
        for tz, existing, reason in skipped_existing:
            if existing is None:
                print(f"  {tz:35s} (no existing mapping) - {reason}")
            else:
                print(f"  {tz:35s} currently {existing} - {reason}")


if __name__ == "__main__":
    main()
