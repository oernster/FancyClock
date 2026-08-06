#!/usr/bin/env python3
"""Repair locale values that were left in English or written incorrectly.

Every locale file carries every reference key, so nothing was ever missing.
What went wrong is quieter: some values are the English string, some are
machine-translation wreckage and some are internally inconsistent with their
own siblings. None of it is visible at runtime, because a value that is
present is used as-is however wrong it is.

Three separate faults are repaired here.

1. ``credits_media`` is English in twenty languages. ``add_credits_media_key``
   carries a table of fifty-one languages against a corpus of seventy-one and
   falls back to English for the rest. Compare ``add_skins_key``, whose table
   is complete, where there is no gap at all. The twenty missing languages are
   supplied below.

2. The Dhivehi month names carry translation debris: a date or a time was
   appended to the month itself, so ``august`` read "August 2019" and
   ``january`` read "January 10:00". The month names themselves were right, so
   the repair is to drop the debris.

3. Individual values that were left in English or written wrongly, listed per
   locale with the reason. The Chinese day names are the largest of these: one
   file mixed three different prefixes across seven days, wrote Saturday with
   an Arabic numeral and left Sunday in English, so the whole set is written
   out consistently rather than patched in one place.

Run from the repository root. The script is idempotent: a value already equal
to its target is left alone and reported as such.
"""

from __future__ import annotations

import json
from pathlib import Path

TRANSLATION_DIR = Path("localization/translations")
REFERENCE_FILE = "key_reference.json"

# --- 1. credits_media, for the twenty languages the original table missed ---
# Meaning: the attribution line for bundled media (sounds and backdrops).
CREDITS_MEDIA_BY_LANGUAGE = {
    "az": "Təşəkkürlər: (Media)",
    "bg": "Заслуги: (Медия)",
    "ca": "Crèdits: (Multimèdia)",
    "dv": "ޝުކުރު: (މީޑިއާ)",
    "dz": "ངོ་བསྟོད། (བརྡ་ལམ།)",
    "fo": "Takkarorð: (Miðlar)",
    "he": "קרדיטים: (מדיה)",
    "kl": "Qujanartut: (Media)",
    "km": "កិត្តិយស៖ (មេឌា)",
    "lo": "ຜູ້ມີສ່ວນຮ່ວມ: (ສື່)",
    "mk": "Заслуги: (Медиуми)",
    "mn": "Талархал: (Медиа)",
    "mt": "Krediti: (Midja)",
    "my": "ကျေးဇူးတင်လွှာ: (မီဒီယာ)",
    "ne": "श्रेय: (मिडिया)",
    "si": "ස්තුතිය: (මාධ්‍ය)",
    "so": "Mahadnaq: (Warbaahin)",
    "ti": "ምስጋና፦ (ሚድያ)",
    "tk": "Sagbolsun: (Media)",
    "to": "Fakamālō: (Mītia)",
}

# --- 2. Dhivehi months, with the appended date and time debris removed ------
DHIVEHI_MONTHS = {
    "january": "ޖެނުއަރީ",
    "february": "ފެބްރުއަރީ",
    "april": "އޭޕްރީލް",
    "july": "ޖުލައި",
    "august": "އޮގަސްޓް",
    "september": "ސެޕްޓެމްބަރު",
    "october": "އޮކްޓޯބަރު",
    "november": "ނޮވެމްބަރު",
    "december": "ޑިސެމްބަރު",
}

# --- 3a. Whole-language corrections, applied to every locale of a language --
# Chinese: one file held 星期一, 週二, 周三 and 週四 across four consecutive
# days, wrote Saturday as 星期6 with an Arabic numeral and left Sunday as the
# English "Sun". 星期 followed by the Chinese numeral is written identically in
# Simplified and Traditional, so one consistent set serves all four locales.
CHINESE_DAYS = {
    "monday": "星期一",
    "tuesday": "星期二",
    "wednesday": "星期三",
    "thursday": "星期四",
    "friday": "星期五",
    "saturday": "星期六",
    "sunday": "星期日",
}

LANGUAGE_FIXES: dict[str, dict[str, str]] = {
    "zh": {
        **CHINESE_DAYS,
        **{f"calendar.days.{day}": text for day, text in CHINESE_DAYS.items()},
    },
    # Romanian: the Cancel button, the import action and the export action were
    # all still the English strings.
    "ro": {
        "cancel": "Anulează",
        "alarm_export": "Exportă...",
        "alarm_import": "Importă...",
    },
    "dv": DHIVEHI_MONTHS,
}

# --- 3b. Single-locale corrections -----------------------------------------
LOCALE_FIXES: dict[str, dict[str, str]] = {
    # "Saab sisse lülitada" means "can be switched on", so the Cancel button
    # said something unrelated. Worse than English, since it reads as an
    # instruction. "About" was never translated.
    "et_EE": {"cancel": "Tühista", "about": "Teave"},
    # Thursday alone was left as "Thu" beside Kedd, Szerda and Péntek.
    "hu_HU": {"thursday": "Csütörtök", "calendar.days.thursday": "Csütörtök"},
    # Thursday alone was left as "Thu" beside the single-letter siblings.
    "lv_LV": {"thursday": "C", "calendar.days.thursday": "C"},
    # May alone was left as the English "May".
    "da_DK": {"may": "Maj"},
    "is_IS": {"may": "Maí"},
}


def language_of(stem: str) -> str:
    """Return the base language code of a locale stem such as ``fr_CA``."""
    return stem.split("_", 1)[0]


def targets_for(stem: str) -> dict[str, str]:
    """Return every key this locale should be corrected to, with its value."""
    language = language_of(stem)
    wanted: dict[str, str] = {}
    wanted.update(LANGUAGE_FIXES.get(language, {}))
    wanted.update(LOCALE_FIXES.get(stem, {}))
    if language in CREDITS_MEDIA_BY_LANGUAGE:
        wanted["credits_media"] = CREDITS_MEDIA_BY_LANGUAGE[language]
    return wanted


def repair(path: Path) -> int:
    """Apply every correction owed to one locale file, returning the count."""
    stem = path.stem
    wanted = targets_for(stem)
    if not wanted:
        return 0

    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        print(f"skipped {path.name}: not a JSON object")
        return 0

    changed = {k: v for k, v in wanted.items() if data.get(k) != v}
    if not changed:
        return 0

    data.update(changed)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"{path.name}: {len(changed)} corrected ({', '.join(sorted(changed))})")
    return len(changed)


def main() -> int:
    if not TRANSLATION_DIR.is_dir():
        print(f"Translation directory not found: {TRANSLATION_DIR}")
        return 1
    files = sorted(
        p for p in TRANSLATION_DIR.glob("*.json") if p.name != REFERENCE_FILE
    )
    total = sum(repair(path) for path in files)
    print(f"\n{total} value(s) corrected across {len(files)} locale file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
