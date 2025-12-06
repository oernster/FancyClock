#!/usr/bin/env python3
import json
import os
from pathlib import Path

# --- CONFIG -------------------------------------------------------------

# Adjust this path if your translations live somewhere else
TRANSLATION_DIR = Path("localization/translations")

# Set this to True if you want to overwrite an existing "skins" key
OVERWRITE_EXISTING = False

# --- TRANSLATIONS FOR "skins" ------------------------------------------
# Meaning: visual themes / appearance styles for the UI.

SKINS_TRANSLATIONS = {
    # A
    "am": "ቅርጾች",
    "ar": "السمات",
    "az": "Dərilər",
    # B
    "be": "Скіны",
    "bg": "Облици",
    "bn": "স্কিনস",
    "bs": "Skinovi",
    # C
    "ca": "Temes",
    "cs": "Vzhledy",
    # D
    "da": "Temaer",
    "de": "Designs",
    "dv": "ސްކިންސް",
    "dz": "གཟུགས་སྒྲིག་",
    # E
    "el": "Θέματα",
    "en": "Skins",
    "es": "Temas",
    "et": "Kujundused",
    # F
    "fa": "پوسته‌ها",
    "fi": "Teemat",
    "fo": "Snið",
    "fr": "Thèmes",
    # H
    "he": "ערכות עיצוב",
    "hi": "स्किन्स",
    "hr": "Skinovi",
    "hu": "Felületek",
    "hy": "Մաշկեր",
    # I
    "id": "Kulit",
    "is": "Skinn",
    "it": "Temi",
    # J
    "ja": "スキン",
    # K
    "ka": "სკინები",
    "kk": "Скиндер",
    "kl": "Iliqutit",
    "km": "ស្បែក",
    "ko": "스킨",
    "ky": "Скиндер",
    # L
    "lo": "ສະກິນ",
    "lt": "Išvaizdos",
    "lv": "Tēmas",
    # M
    "mg": "Hoditra",
    "mk": "Скинови",
    "mn": "Арьсууд",
    "ms": "Kulit",
    "mt": "Temi",
    "my": "စကင်းများ",
    # N
    "nb": "Temaer",
    "ne": "स्किनहरू",
    "nl": "Thema’s",
    # P
    "pl": "Skórki",
    "pt": "Temas",
    # R
    "ro": "Skinuri",
    "ru": "Скины",
    "rw": "Imisusire",
    # S
    "si": "තේමා",
    "sk": "Vzhľady",
    "sl": "Preobleke",
    "so": "Maqaarrada",
    "sq": "Lëkurët",
    "sr": "Скинови",
    "sv": "Teman",
    # T
    "tg": "Пӯстҳо",
    "th": "สกิน",
    "ti": "ቆዳታት",
    "tk": "Gabyklary",
    "to": "Ngaahi kili",
    "tr": "Kaplamalar",
    # U
    "uk": "Скіни",
    "ur": "اسکنز",
    "uz": "Terilar",
    # V
    "vi": "Giao diện",
    # Z / Chinese variants
    "zh": "皮肤",        # generic zh → Simplified
    # If you want to special-case Traditional, we can override later per locale
}

# Special overrides for some locales that share the same base language
# but need different wording (e.g. zh_TW vs zh_CN).
LOCALE_OVERRIDES = {
    "zh_TW": "皮膚",
    "zh_HK": "皮膚",
    "zh_MO": "皮膚",
}


# --- IMPLEMENTATION -----------------------------------------------------


def get_language_code_from_filename(filename: str) -> str:
    """
    Extract base language code from a filename like 'fr_FR.json' -> 'fr'.
    """
    name = filename.split(".", 1)[0]  # 'fr_FR'
    return name.split("_", 1)[0]      # 'fr'


def get_skins_translation(locale_name: str) -> str:
    """
    Get the translation for 'skins' based on a full locale name like 'fr_FR'.
    Preference order:
    1) Exact locale override in LOCALE_OVERRIDES
    2) Base language in SKINS_TRANSLATIONS
    3) Fallback to English 'Skins'
    """
    # Exact override: e.g. zh_TW
    if locale_name in LOCALE_OVERRIDES:
        return LOCALE_OVERRIDES[locale_name]

    lang = get_language_code_from_filename(locale_name)
    return SKINS_TRANSLATIONS.get(lang, SKINS_TRANSLATIONS["en"])


def process_file(path: Path) -> None:
    """
    Load a JSON file, add 'skins' key if missing (or overwrite if configured),
    then write back.
    """
    locale_name = path.name  # e.g. 'fr_FR.json'

    # Skip any reference key file if you don't want to touch it
    if locale_name == "key_reference.json":
        print(f"Skipping reference file: {path}")
        return

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR reading {path}: {e}")
        return

    if not isinstance(data, dict):
        print(f"WARNING: {path} does not contain a JSON object at top level; skipping.")
        return

    if "skins" in data and not OVERWRITE_EXISTING:
        print(f"'skins' already in {path}, leaving as-is.")
        return

    translation_value = get_skins_translation(locale_name)
    data["skins"] = translation_value

    try:
        with path.open("w", encoding="utf-8") as f:
            # keep it reasonably pretty & UTF-8
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        print(f"Updated {path} with skins = {translation_value!r}")
    except Exception as e:
        print(f"ERROR writing {path}: {e}")


def main():
    if not TRANSLATION_DIR.is_dir():
        print(f"Translation directory not found: {TRANSLATION_DIR}")
        return

    for entry in TRANSLATION_DIR.iterdir():
        if entry.is_file() and entry.suffix == ".json":
            process_file(entry)


if __name__ == "__main__":
    main()
