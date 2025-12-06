#!/usr/bin/env python3
import json
import os

MAP_PATH = os.path.join("localization", "timezone_locale_map.json")

def main():
    with open(MAP_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Argentinian timezone → locale mappings:\n")
    for tz, loc in sorted(data.items()):
        if "Argentina" in tz or tz.endswith("/Buenos_Aires"):
            print(f"{tz:40s} -> {loc}")

if __name__ == "__main__":
    main()
