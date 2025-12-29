#!/usr/bin/env python3
import json
from pathlib import Path

# ---- CONFIG ------------------------------------------------------------

# Adjust if your translations live elsewhere
TRANSLATION_DIR = Path("localization/translations")

# Set True if you want to overwrite an existing "credits_media" key
OVERWRITE_EXISTING = False

# ---- TRANSLATIONS FOR "credits_media" ---------------------------------
# Meaning: "Credits: (Media)" – heading in the About dialog.
# For any language not listed here, we fall back to English.

CREDITS_MEDIA_TRANSLATIONS = {
    # Generic / fallback
    "en": "Credits: (Media)",
    # Arabic
    "ar": "اعتمادات: (الوسائط)",
    # German
    "de": "Danksagungen: (Medien)",
    # Spanish
    "es": "Créditos: (medios)",
    # French
    "fr": "Crédits : (médias)",
    # Italian
    "it": "Crediti: (media)",
    # Portuguese
    "pt": "Créditos: (mídia)",
    # Russian
    "ru": "Благодарности: (медиа)",
    # Dutch
    "nl": "Credits: (media)",
    # Swedish
    "sv": "Tack: (media)",
    # Norwegian Bokmål
    "nb": "Takk: (media)",
    # Danish
    "da": "Credits: (medier)",
    # Finnish
    "fi": "Tekijät: (media)",
    # Polish
    "pl": "Podziękowania: (media)",
    # Czech
    "cs": "Poděkování: (média)",
    # Slovak
    "sk": "Poďakovanie: (médiá)",
    # Slovenian
    "sl": "Zahvale: (mediji)",
    # Hungarian
    "hu": "Köszönet: (média)",
    # Romanian
    "ro": "Mulțumiri: (media)",
    # Greek
    "el": "Ευχαριστίες: (μέσα)",
    # Turkish
    "tr": "Teşekkürler: (medya)",
    # Ukrainian
    "uk": "Подяки: (медіа)",
    # Belarusian
    "be": "Падзякі: (медыа)",
    # Serbian / Bosnian / Croatian (Latin/Cyrillic)
    "sr": "Захвалнице: (медији)",
    "bs": "Zahvale: (mediji)",
    "hr": "Zahvale: (mediji)",
    # Albanian
    "sq": "Falënderime: (media)",
    # Russian-family minor
    "kk": "Алғыстар: (медиа)",
    "ky": "Ыраазычылык: (медиа)",
    "tg": "Ташаккур: (расонаҳо)",
    "uz": "Minnatdorchilik: (media)",
    # Chinese (generic zh → simplified)
    "zh": "致谢：（媒体）",
    # Japanese
    "ja": "クレジット（メディア）",
    # Korean
    "ko": "크레딧 (미디어)",
    # Vietnamese
    "vi": "Lời cảm ơn: (phương tiện)",
    # Hindi
    "hi": "श्रेय: (मीडिया)",
    # Bengali
    "bn": "ক্রেডিট: (মিডিয়া)",
    # Urdu
    "ur": "شکریہ: (میڈیا)",
    # Persian
    "fa": "تقدیرنامه: (رسانه)",
    # Thai
    "th": "เครดิต: (สื่อ)",
    # Indonesian / Malay
    "id": "Kredit: (media)",
    "ms": "Kredit: (media)",
    # Swahili-ish Kinyarwanda (rough but better than English)
    "rw": "Ishimwe: (itangazamakuru)",
    # Amharic (approx.)
    "am": "ምስጋና፡ (መገናኛ መረብ)",
    # Armenian
    "hy": "Շնորհակալություն․ (մեդիա)",
    # Georgian
    "ka": "მადლობები: (მედია)",
    # Lithuanian / Latvian / Estonian
    "lt": "Padėkos: (medija)",
    "lv": "Pateicība: (mēdiji)",
    "et": "Tänu: (meedia)",
    # Icelandic
    "is": "Þakkir: (miðlar)",
    # Malagasy (rough)
    "mg": "Fisaorana: (media)",
}

# Special overrides for specific locales that should differ
LOCALE_OVERRIDES = {
    "zh_TW": "致謝：（媒體）",
    "zh_HK": "致謝：（媒體）",
    "zh_MO": "致謝：（媒體）",
}


# ---- IMPLEMENTATION ----------------------------------------------------


def get_language_code_from_filename(filename: str) -> str:
    """
    Extract base language code from a filename like 'fr_FR.json' -> 'fr'.
    """
    name = filename.split(".", 1)[0]  # 'fr_FR'
    return name.split("_", 1)[0]  # 'fr'


def get_credits_media_translation(locale_name: str) -> str:
    """
    Get the translation for 'credits_media' based on a full locale file name,
    e.g. 'fr_FR.json'.

    Priority:
      1) Exact locale override in LOCALE_OVERRIDES
      2) Base language in CREDITS_MEDIA_TRANSLATIONS
      3) Fallback to English 'Credits: (Media)'
    """
    # Remove .json
    base = locale_name.split(".json", 1)[0]

    # 1. exact locale override (e.g. zh_TW)
    if base in LOCALE_OVERRIDES:
        return LOCALE_OVERRIDES[base]

    # 2. base language mapping
    lang = get_language_code_from_filename(locale_name)
    if lang in CREDITS_MEDIA_TRANSLATIONS:
        return CREDITS_MEDIA_TRANSLATIONS[lang]

    # 3. default fallback
    return CREDITS_MEDIA_TRANSLATIONS["en"]


def process_file(path: Path) -> None:
    """
    Load a JSON file, add/update 'credits_media', then write back.
    """
    filename = path.name

    # Skip key reference if you like
    if filename == "key_reference.json":
        print(f"Skipping reference file: {path}")
        return

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR reading {path}: {e}")
        return

    if not isinstance(data, dict):
        print(f"WARNING: {path} does not contain a top-level JSON object; skipping.")
        return

    if "credits_media" in data and not OVERWRITE_EXISTING:
        print(f"'credits_media' already in {path}, leaving as-is.")
        return

    value = get_credits_media_translation(filename)
    data["credits_media"] = value

    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        print(f"Updated {path} with credits_media = {value!r}")
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
