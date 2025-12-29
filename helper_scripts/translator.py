import json
import os


class Translator:
    def __init__(self, locale_code="en_GB"):
        self.locale_code = locale_code
        self.translations = self.load_translations()

    def load_translations(self):
        """Load translations from the JSON file for the current locale."""
        path = os.path.join(
            os.path.dirname(__file__),
            "localization",
            "translations",
            f"{self.locale_code}.json",
        )
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            msg = (
                f"Translation file not found for {self.locale_code}, "
                "falling back to en_GB."
            )
            print(msg)
            # Fallback to a default language if the file for the specified locale
            # is not found.
            default_path = os.path.join(
                os.path.dirname(__file__),
                "localization",
                "translations",
                "en_GB.json",
            )
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)

    def translate(self, key):
        """Translate a given key using the loaded translations."""
        # Simple split for now, assuming format "locale_KEY"
        # This logic is flawed for keys that contain underscores but are not prefixed.
        # For example, 'about_dialog_title' would be split into a list.
        # The correct approach is to check for a specific prefix pattern.
        # A simple `get` will suffice since the prefixes are removed from the JSON
        # files.
        return self.translations.get(key, key)
