#!/usr/bin/env python3
"""Add the eight update-check keys to every locale.

The translations live in ``update_check_translations.json`` beside this
script: they are data, not code. Every language in the corpus is covered
and there is no English default: a language absent from the data is an
error raised here rather than a silent English string in a shipped file,
which is exactly the fault the translation-coverage tests exist to catch.

``update_available_text`` substitutes ``{latest}`` and ``{current}`` at
runtime, so every translation has to keep both tokens exactly as written.
"""

from __future__ import annotations

import json
from pathlib import Path

TRANSLATION_DIR = Path("localization/translations")
REFERENCE_FILE = "key_reference.json"
DATA_FILE = Path(__file__).resolve().parent / "update_check_translations.json"

TEXT_KEY = "update_available_text"
REQUIRED_TOKENS = ("{latest}", "{current}")

EXPECTED_KEYS = frozenset(
    [
        "check_for_updates",
        "update_available_title",
        TEXT_KEY,
        "update_download",
        "update_skip",
        "update_later",
        "update_up_to_date",
        "update_check_failed",
    ]
)


def load_tables() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Return the per-language and per-locale-override tables."""
    with DATA_FILE.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data["languages"], data["locale_overrides"]


def language_of(stem: str) -> str:
    """Return the base language code of a locale stem such as ``pt_BR``."""
    return stem.split("_", 1)[0]


def values_for(
    stem: str,
    languages: dict[str, dict[str, str]],
    overrides: dict[str, dict[str, str]],
) -> dict[str, str]:
    """Return all key values for one locale, raising if the language is absent."""
    if stem in overrides:
        values = dict(overrides[stem])
    else:
        language = language_of(stem)
        if language not in languages:
            raise KeyError(
                f"no translation for language {language!r} (locale {stem!r}). "
                "Add it rather than letting English be shipped."
            )
        values = dict(languages[language])
    if set(values) != EXPECTED_KEYS:
        raise ValueError(f"{stem}: key set mismatch: {sorted(values)}")
    for token in REQUIRED_TOKENS:
        if token not in values[TEXT_KEY]:
            raise ValueError(f"{stem}: the {TEXT_KEY} translation lost {token}")
    return values


def apply(path: Path, values: dict[str, str]) -> int:
    """Write the keys into one locale file, returning how many changed."""
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
    languages, overrides = load_tables()
    files = sorted(
        p for p in TRANSLATION_DIR.glob("*.json") if p.name != REFERENCE_FILE
    )
    total = 0
    for path in files:
        total += apply(path, values_for(path.stem, languages, overrides))
    print(f"{total} value(s) written across {len(files)} locale file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
