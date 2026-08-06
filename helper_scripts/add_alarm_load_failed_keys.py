#!/usr/bin/env python3
"""Add the two "alarms could not be read" keys to every locale.

Shown once at startup when the saved alarms document did not load whole. The
count is substituted into ``{count}`` by the caller, so every translation has
to keep that token exactly as written.

The wording deliberately avoids grammatical agreement with the number.
"Damaged entries skipped: 3" needs no plural form, no gender and no case,
which is what makes one sentence safe to carry into seventy-one languages. A
phrasing such as "3 entries were skipped" would need a different form per
language for one, two and many, so it would be wrong in most of them.

The translations live in ``alarm_load_failed_translations.json`` beside this
script rather than in a table here. They are data, not code: sentences in
seventy-one scripts cannot be wrapped to a source line limit without a
formatter joining them back up again. A JSON file is also what the rest of
this project's localisation already looks like.

Every language in the corpus is covered. There is no English default: a
language absent from the data is an error raised here rather than a silent
English string in a shipped file, which is exactly the fault that left twenty
languages of ``credits_media`` reading English for years.
"""

from __future__ import annotations

import json
from pathlib import Path

TRANSLATION_DIR = Path("localization/translations")
REFERENCE_FILE = "key_reference.json"
DATA_FILE = Path(__file__).resolve().parent / "alarm_load_failed_translations.json"

TITLE_KEY = "alarms_load_failed_title"
TEXT_KEY = "alarms_load_failed_text"
COUNT_TOKEN = "{count}"


def load_tables() -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, str]]]:
    """Return the title, text and locale-override tables from the data file."""
    with DATA_FILE.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data["titles"], data["texts"], data["locale_overrides"]


def language_of(stem: str) -> str:
    """Return the base language code of a locale stem such as ``pt_BR``."""
    return stem.split("_", 1)[0]


def values_for(
    stem: str,
    titles: dict[str, str],
    texts: dict[str, str],
    overrides: dict[str, dict[str, str]],
) -> dict[str, str]:
    """Return both key values for one locale, raising if the language is absent."""
    if stem in overrides:
        values = dict(overrides[stem])
    else:
        language = language_of(stem)
        if language not in titles or language not in texts:
            raise KeyError(
                f"no translation for language {language!r} (locale {stem!r}). "
                "Add it rather than letting English be shipped."
            )
        values = {TITLE_KEY: titles[language], TEXT_KEY: texts[language]}
    if COUNT_TOKEN not in values[TEXT_KEY]:
        raise ValueError(f"{stem}: the {TEXT_KEY} translation lost {COUNT_TOKEN}")
    return values


def apply(path: Path, values: dict[str, str]) -> int:
    """Write both keys into one locale file, returning how many changed."""
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    changed = {k: v for k, v in values.items() if data.get(k) != v}
    if not changed:
        return 0
    data.update(changed)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return len(changed)


def main() -> int:
    if not TRANSLATION_DIR.is_dir():
        print(f"Translation directory not found: {TRANSLATION_DIR}")
        return 1
    titles, texts, overrides = load_tables()
    files = sorted(
        p for p in TRANSLATION_DIR.glob("*.json") if p.name != REFERENCE_FILE
    )
    total = 0
    for path in files:
        total += apply(path, values_for(path.stem, titles, texts, overrides))
    print(f"{total} value(s) written across {len(files)} locale file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
