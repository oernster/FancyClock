#!/usr/bin/env python3
import ast
import json
import os
from copy import deepcopy

BASE = os.path.join("localization", "translations")

def main():
    changed_files = []

    for fname in sorted(os.listdir(BASE)):
        if not fname.endswith(".json"):
            continue

        path = os.path.join(BASE, fname)
        lang = fname.split("_")[0]

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        original = deepcopy(data)
        modified = False

        # Only touch Arabic locales (ar_*)
        if lang == "ar":
            # 1) Fix digits: convert string "['٠','١',...]" to proper list
            digits = data.get("digits")
            if isinstance(digits, str):
                try:
                    parsed = ast.literal_eval(digits)
                    if isinstance(parsed, (list, tuple)) and len(parsed) == 10:
                        data["digits"] = list(parsed)
                        modified = True
                except Exception:
                    # If it fails, just leave as-is
                    pass

            # 2) Fix timezone: derive from select_timezone_title if possible
            if data.get("timezone") == "Timezone":
                title = data.get("select_timezone_title")
                if isinstance(title, str) and " " in title:
                    # Example: "تحديد المنطقة الزمنية" -> "المنطقة الزمنية"
                    data["timezone"] = title.split(" ", 1)[1]
                else:
                    # Fallback
                    data["timezone"] = "المنطقة الزمنية"
                modified = True

            # 3) Fix help: "النجدة" -> "مساعدة"
            if data.get("help") == "النجدة":
                data["help"] = "مساعدة"
                modified = True

        if modified and data != original:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            changed_files.append(fname)

    print("Updated Arabic locales:", ", ".join(changed_files) or "none")

if __name__ == "__main__":
    main()
