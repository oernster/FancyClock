#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

LOG = logging.getLogger("translate_timezones")

# ---------------------------------------------------------------------------
# Language → LibreTranslate target language fallbacks
# ---------------------------------------------------------------------------

# For each language code (from filename, e.g. "es" from "es_ES.json"),
# try these candidates *in order* as LibreTranslate "target" codes.
# If none are supported by the server, we finally fall back to "en".
LANGUAGE_FALLBACKS: Dict[str, List[str]] = {
    # Major languages that LibreTranslate usually supports directly
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
    "zh": ["zh-Hans", "zh-Hant", "en"],  # map generic zh → zh-Hans/zh-Hant
    # For anything we don’t know, we’ll eventually fall back to "en"
}

# Source language: keys in key_reference.json are English
SOURCE_LANG = "en"

# Reference filename inside the translations dir
REFERENCE_FILENAME = "key_reference.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_supported_languages(api_url: str) -> List[str]:
    url = api_url.rstrip("/") + "/languages"
    LOG.info("Fetching supported languages from LibreTranslate...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # "data" is a list of { code: "...", name: "..." }
    codes = [item["code"] for item in data]
    LOG.info("LibreTranslate supports %d languages: %s", len(codes), ", ".join(codes))
    return codes


def resolve_target_language(lang: str, supported: List[str]) -> str:
    """
    Given a base language (e.g. 'es' from 'es_AR'),
    return a LibreTranslate language code to use as target.
    Always returns *something* (worst case 'en').
    """
    supported_set = set(supported)

    # Get candidate list from our mapping, or default to [lang, 'en'].
    candidates = LANGUAGE_FALLBACKS.get(lang, [lang, "en"])

    for cand in candidates:
        if cand in supported_set:
            LOG.debug("Resolved language '%s' → target '%s'", lang, cand)
            return cand

    # Final fallback – should basically never happen, because 'en' is always there
    LOG.warning("No candidate target language for '%s' found in supported set, falling back to 'en'", lang)
    return "en"


def load_json(path: Path) -> Dict[str, str]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, str]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    temp_path.replace(path)


def detect_locale_and_language(path: Path) -> Tuple[str, str]:
    """
    From filename 'es_AR.json' return ('es_AR', 'es').
    """
    base = path.stem  # e.g. 'es_AR'
    parts = base.split("_", 1)
    language = parts[0]
    return base, language


def translate_batch(
    api_url: str,
    texts: List[str],
    source_lang: str,
    target_lang: str,
    dry_run: bool = False,
) -> List[str]:
    """
    Translate a batch of strings using LibreTranslate.
    Uses repeated 'q' fields in form data; handles various response shapes.
    """
    if dry_run:
        # Just echo back for simulation
        return texts

    if not texts:
        return []

    url = api_url.rstrip("/") + "/translate"

    payload = {
        "source": source_lang,
        "target": target_lang,
        "format": "text",
    }

    # 'q' is a list, requests will encode as repeated q=params
    data = {**payload, "q": texts}
    resp = requests.post(url, data=data, timeout=120)
    resp.raise_for_status()
    j = resp.json()

    # LibreTranslate usually returns a list of dicts with translatedText
    if isinstance(j, list):
        out: List[str] = []
        for item in j:
            if isinstance(item, dict) and "translatedText" in item:
                out.append(item["translatedText"])
            else:
                out.append(str(item))
        return out

    # Or a single dict
    if isinstance(j, dict) and "translatedText" in j:
        return [j["translatedText"]]

    # Fallback: try to coerce to strings
    LOG.warning("Unexpected LibreTranslate response shape: %r", j)
    if isinstance(j, list):
        return [str(x) for x in j]
    return [str(j)]


# ---------------------------------------------------------------------------
# Core per-locale processing
# ---------------------------------------------------------------------------

def process_locale(
    file_path: Path,
    reference: Dict[str, str],
    supported_langs: List[str],
    api_url: str,
    force: bool = False,
    dry_run: bool = False,
) -> Tuple[str, bool, Optional[str]]:
    """
    Process a single locale JSON file.
    Returns (filename, success:bool, error_message_or_None)
    """
    try:
        locale, language = detect_locale_and_language(file_path)
        LOG.info("Processing %s -> locale=%s, language=%s", file_path.name, locale, language)

        # Load existing data
        current = load_json(file_path)

        ref_keys = set(reference.keys())
        cur_keys = set(current.keys())

        missing_keys = sorted(ref_keys - cur_keys)
        extra_keys = sorted(cur_keys - ref_keys)

        if extra_keys:
            LOG.debug("  %s has %d extra keys not in reference (keeping them).", file_path.name, len(extra_keys))

        if not missing_keys and not force:
            LOG.info("All keys already present for %s. No translation needed; marking as done.", file_path.name)
            return (file_path.name, True, None)

        target_lang = resolve_target_language(language, supported_langs)
        LOG.info("  Using target language '%s' for locale '%s' (base '%s')", target_lang, locale, language)

        # If force: retranslate all reference keys, ignoring existing values
        keys_to_translate = sorted(ref_keys) if force else missing_keys

        if not keys_to_translate:
            LOG.info("  Nothing to translate for %s.", file_path.name)
            return (file_path.name, True, None)

        LOG.info("  Translating %d keys for %s", len(keys_to_translate), file_path.name)

        batch_size = 50
        for i in range(0, len(keys_to_translate), batch_size):
            batch_keys = keys_to_translate[i : i + batch_size]
            batch_texts = [reference[k] for k in batch_keys]

            LOG.debug(
                "  %s: translating batch %d-%d (%d items)",
                file_path.name,
                i,
                i + len(batch_keys) - 1,
                len(batch_keys),
            )

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

        # Optionally overwrite *only* missing keys when not forcing
        if not dry_run:
            save_json(file_path, current)
            LOG.info("  Saved translations for %s", file_path.name)
        else:
            LOG.info("  Dry-run: NOT writing changes for %s", file_path.name)

        return (file_path.name, True, None)

    except Exception as e:
        LOG.error("Error processing %s: %s", file_path.name, e)
        return (file_path.name, False, str(e))


# ---------------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------------

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
        help="Force re-translation of *all* keys, even if file already complete.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do everything except actually calling the API and writing files.",
    )
    parser.add_argument(
        "-v", "--verbose",
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
        raise SystemExit(f"Reference file not found: {reference_file} (expected {REFERENCE_FILENAME} in translations dir)")

    LOG.info("Loading reference file: %s", reference_file)
    reference = load_json(reference_file)

    # Locale files: all *.json except the reference file
    locale_files = sorted(
        p for p in translations_dir.glob("*.json")
        if p.name != REFERENCE_FILENAME
    )

    LOG.info("Found %d locale files to process.", len(locale_files))
    for p in locale_files:
        LOG.info("  - %s", p.name)

    if not locale_files:
        LOG.warning("No locale files found. Nothing to do.")
        return

    supported_langs = fetch_supported_languages(args.api_url)

    # Workers
    if args.workers <= 0:
        try:
            import multiprocessing
            workers = max(1, multiprocessing.cpu_count())
        except Exception:
            workers = 4
    else:
        workers = max(1, args.workers)

    LOG.info("Starting translation with %d worker threads.", workers)

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
    if failures > 0:
        LOG.warning("Some files failed to translate. Check logs above for details.")


if __name__ == "__main__":
    main()
