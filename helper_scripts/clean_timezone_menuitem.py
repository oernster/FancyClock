import glob
import json
import os

BASE = "./localization/translations"

for path in glob.glob(os.path.join(BASE, "*.json")):
    if os.path.basename(path) == "key_reference.json":
        continue

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # If the key exists and is still English, remove it
    if data.get("timezone") == "Timezone":
        print("Removing timezone from", path)
        del data["timezone"]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
