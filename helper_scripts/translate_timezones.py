#!/usr/bin/env python3
"""Timezone translation CLI.

The bulk of shared helpers should live in
`helper_scripts/translate_timezones_lib.py`.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from helper_scripts.translate_timezones_lib import (
    SOURCE_LANG,
    fetch_supported_languages,
    load_json,
    save_json,
)

LOG = logging.getLogger("translate_timezones")

REFERENCE_FILENAME = "key_reference.json"

LANGUAGE_FALLBACKS: Dict[str, List[str]] = {
    "ar": ["ar", "en"],
    "az": ["az", "tr", "en"],
    "bg": ["bg", "ru", "en"],
    "bn": ["bn", "en"],
    "bs": ["bs", "sr", "hr", "en"],
    "ca": ["ca", "es", "en"],
    "cs": ["cs", "sk", "en"],
    "da": ["da", "nb", "sv", "en"],
    "de": ["de", "en"],
    "el": ["el", "en"],
    "es": ["es", "pt", "en"],
    "et": ["et", "fi", "en"],
    "fa": ["fa", "ur", "en"],
    "fi": ["fi", "sv", "en"],
    "fr": ["fr", "en"],
    "he": ["he", "ar", "en"],
    "hi": ["hi", "en"],
    "hr": ["hr", "sr", "en"],
    "hu": ["hu", "en"],
    "id": ["id", "ms", "en"],
    "is": ["is", "en"],
    "it": ["it", "en"],
    "ja": ["ja", "en"],
    "ka": ["ka", "ru", "en"],
    "kk": ["kk", "ru", "en"],
    "km": ["km", "th", "en"],
    "ko": ["ko", "en"],
    "ky": ["ky", "ru", "en"],
    "lo": ["lo", "th", "en"],
    "lt": ["lt", "en"],
    "lv": ["lv", "lt", "en"],
    "mg": ["mg", "fr", "en"],
    "mk": ["mk", "ru", "en"],
    "mn": ["mn", "ru", "en"],
    "ms": ["ms", "id", "en"],
    "mt": ["mt", "it", "en"],
    "my": ["my", "th", "en"],
    "nb": ["nb", "nn", "sv", "en"],
    "ne": ["ne", "en"],
    "nl": ["nl", "de", "en"],
    "pl": ["pl", "cs", "en"],
    "pt": ["pt", "es", "en"],
    "ro": ["ro", "it", "en"],
    "ru": ["ru", "en"],
    "rw": ["rw", "fr", "en"],
    "si": ["si", "en"],
    "sk": ["sk", "cs", "en"],
    "sl": ["sl", "hr", "en"],
    "so": ["so", "en"],
    "sq": ["sq", "en"],
    "sr": ["sr", "bs", "ru", "en"],
    "sv": ["sv", "nb", "da", "en"],
    "tg": ["tg", "ru", "en"],
    "ti": ["ti", "en"],
    "tk": ["tk", "tr", "en"],
    "to": ["to", "en"],
    "tr": ["tr", "en"],
    "uk": ["uk", "ru", "en"],
    "ur": ["ur", "fa", "en"],
    "uz": ["uz", "ru", "en"],
    "vi": ["vi", "en"],
    "zh": ["zh-Hans", "zh-Hant", "en"],
}


def resolve_target_language(lang: str, supported: List[str]) -> str:
    supported_set = set(supported)
    candidates = LANGUAGE_FALLBACKS.get(lang, [lang, "en"])
    for cand in candidates:
        if cand in supported_set:
            LOG.debug("Resolved language '%s' -> target '%s'", lang, cand)
            return cand

    LOG.warning(
        "No candidate target language for '%s' found in supported set; "
        "falling back to 'en'",
        lang,
    )
    return "en"


def detect_locale_and_language(path: Path) -> Tuple[str, str]:
    base = path.stem
    language = base.split("_", 1)[0]
    return base, language


def translate_batch(
    api_url: str,
    texts: List[str],
    source_lang: str,
    target_lang: str,
    dry_run: bool = False,
) -> List[str]:
    if dry_run:
        return texts

    if not texts:
        return []

    url = api_url.rstrip("/") + "/translate"
    payload = {"source": source_lang, "target": target_lang, "format": "text"}
    data = {**payload, "q": texts}

    resp = requests.post(url, data=data, timeout=120)
    resp.raise_for_status()
    j = resp.json()

    if isinstance(j, list):
        out: List[str] = []
        for item in j:
            if isinstance(item, dict) and "translatedText" in item:
                out.append(item["translatedText"])
            else:
                out.append(str(item))
        return out

    if isinstance(j, dict) and "translatedText" in j:
        return [j["translatedText"]]

    LOG.warning("Unexpected LibreTranslate response shape: %r", j)
    if isinstance(j, list):
        return [str(x) for x in j]
    return [str(j)]


def process_locale(
    file_path: Path,
    reference: Dict[str, str],
    supported_langs: List[str],
    api_url: str,
    force: bool = False,
    dry_run: bool = False,
) -> Tuple[str, bool, Optional[str]]:
    try:
        locale, language = detect_locale_and_language(file_path)
        LOG.info(
            "Processing %s -> locale=%s, language=%s", file_path.name, locale, language
        )

        current = load_json(file_path)

        ref_keys = set(reference.keys())
        cur_keys = set(current.keys())
        missing_keys = sorted(ref_keys - cur_keys)

        if not missing_keys and not force:
            msg = (
                "All keys already present for %s. "
                "No translation needed; marking as done."
            )
            LOG.info(msg, file_path.name)
            return (file_path.name, True, None)

        target_lang = resolve_target_language(language, supported_langs)
        LOG.info(
            "Using target language '%s' for locale '%s' (base '%s')",
            target_lang,
            locale,
            language,
        )

        keys_to_translate = sorted(ref_keys) if force else missing_keys
        if not keys_to_translate:
            return (file_path.name, True, None)

        batch_size = 50
        for i in range(0, len(keys_to_translate), batch_size):
            batch_keys = keys_to_translate[i : i + batch_size]
            batch_texts = [reference[k] for k in batch_keys]
            translations = translate_batch(
                api_url=api_url,
                texts=batch_texts,
                source_lang=SOURCE_LANG,
                target_lang=target_lang,
                dry_run=dry_run,
            )
            if len(translations) != len(batch_keys):
                raise RuntimeError(
                    f"Translation batch size mismatch for {file_path.name}: "
                    f"got {len(translations)} translations for {len(batch_keys)} keys."
                )
            for key, translated in zip(batch_keys, translations):
                current[key] = translated

        if not dry_run:
            save_json(file_path, current)
            LOG.info("Saved translations for %s", file_path.name)

        return (file_path.name, True, None)

    except Exception as exc:
        LOG.error("Error processing %s: %s", file_path.name, exc)
        return (file_path.name, False, str(exc))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--translations-dir",
        default="./localization/translations",
        help="Directory containing locale JSON files (default: %(default)s)",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("LT_API_URL", "http://localhost:5000"),
        help="LibreTranslate API base URL (default: %(default)s or LT_API_URL env)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Number of worker threads to use (default: CPU count, min 1)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-translation of all keys, even if file already complete.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do everything except calling the API and writing files.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging (DEBUG).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    translations_dir = Path(args.translations_dir).resolve()
    LOG.info("Using translations directory: %s", translations_dir)

    reference_file = translations_dir / REFERENCE_FILENAME
    if not reference_file.is_file():
        msg = (
            f"Reference file not found: {reference_file} "
            f"(expected {REFERENCE_FILENAME} in translations dir)"
        )
        raise SystemExit(msg)

    reference = load_json(reference_file)
    locale_files = sorted(
        p for p in translations_dir.glob("*.json") if p.name != REFERENCE_FILENAME
    )

    supported_langs = fetch_supported_languages(args.api_url)

    if args.workers <= 0:
        try:
            import multiprocessing

            workers = max(1, multiprocessing.cpu_count())
        except Exception:
            workers = 4
    else:
        workers = max(1, args.workers)

    successes = 0
    failures = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                process_locale,
                file_path=p,
                reference=reference,
                supported_langs=supported_langs,
                api_url=args.api_url,
                force=args.force,
                dry_run=args.dry_run,
            )
            for p in locale_files
        ]

        for fut in concurrent.futures.as_completed(futures):
            filename, ok, err = fut.result()
            if ok:
                successes += 1
            else:
                failures += 1
                LOG.error("Failed: %s (%s)", filename, err)

    LOG.info("Translation finished: %d succeeded, %d failed.", successes, failures)
    if failures:
        LOG.warning("Some files failed to translate. Check logs above for details.")


if __name__ == "__main__":
    main()
