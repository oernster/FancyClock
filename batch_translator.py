import json
import os
import time
import multiprocessing
import functools
from translate import Translator
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import logging


# --- Debug logging configuration ---
LOG_FILE = os.environ.get("BATCH_TRANSLATOR_LOG_FILE", "batch_translator_debug.log")

logger = logging.getLogger("batch_translator")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    # Only log to file (stdout/stderr is already used by tqdm)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fmt = logging.Formatter(
        "%(asctime)s [%(process)d:%(threadName)s] %(levelname)s %(message)s"
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

# --- Core configuration ---
CPU_COUNT = os.cpu_count() or 1
MAX_PROCESSES = min(12, CPU_COUNT)

DONE_SUFFIX = ".done"  # marker file suffix to remember completed translations


# Global API rate limiting (shared across all worker processes)
REQUESTS_PER_SECOND = 0.2   # tweak if needed
BASE_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 30.0
MAX_TRANSIENT_ATTEMPTS = 4

# Hard timeout for a single external translation call (seconds)
TRANSLATE_CALL_TIMEOUT_SECONDS = 5.0


# --- Language fallbacks ------------------------------------------------------
# Some locale language codes are not supported by the translation backend,
# but people in those locales commonly speak another language that *is*
# supported. In such cases we map:
#
#   raw locale language -> effective language used for translation
#
# You can extend this mapping as you discover more cases.
LANGUAGE_FALLBACKS: dict[str, str] = {
    # Greenlandic (Kalaallisut) -> Danish
    # Google Translate does not support "kl", but Danish ("da") is widely used.
    "kl": "da",
    "fy": "nl",   # Frisian -> Dutch
    "lb": "de",   # Luxembourgish -> German
}


def resolve_effective_language(raw_language: str) -> tuple[str, bool]:
    """
    Given the raw language code from the locale (e.g. 'kl' from 'kl_GL.json'),
    return a tuple:

        (effective_language, is_fallback)

    - effective_language is the language code we will actually send to the
      translation backend and use for caching / reference-files.
    - is_fallback is True if we had to substitute a different language
      from LANGUAGE_FALLBACKS.
    """
    if raw_language in LANGUAGE_FALLBACKS:
        return LANGUAGE_FALLBACKS[raw_language], True
    return raw_language, False

def get_target_language(file_path: str) -> str:
    """
    Extract language code from file name.
    Example: 'fr_FR.json' -> 'fr'
    """
    file_name = os.path.basename(file_path)
    base_name = os.path.splitext(file_name)[0]
    language_code = base_name.split("_")[0]
    return language_code


def cooperative_sleep(seconds: float, control_state) -> None:
    """
    Sleep in small chunks so we can react quickly to a stop signal.
    """
    end = time.time() + seconds
    while True:
        if control_state.get("stop"):
            raise KeyboardInterrupt()
        now = time.time()
        if now >= end:
            break
        chunk = min(0.5, end - now)
        time.sleep(chunk)


def init_language_key_cache(translations_dir: str, source_data: dict) -> dict:
    """
    Build an initial cache of existing translations from all current JSON files.

    Returns:
        lang_key_cache: { effective_language_code -> { key -> translated_string } }

    - effective_language_code is the language actually used for translation,
      after applying LANGUAGE_FALLBACKS (e.g. 'kl_GL' contributes to 'da').
    """
    cache: dict[str, dict[str, str]] = {}

    for fname in os.listdir(translations_dir):
        if not fname.endswith(".json"):
            continue
        if fname in ["en_GB.json", "key_reference.json"]:
            continue

        path = os.path.join(translations_dir, fname)
        raw_lang = get_target_language(path)
        effective_lang, _ = resolve_effective_language(raw_lang)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            # Skip unreadable / broken files
            continue

        lang_cache = cache.setdefault(effective_lang, {})

        for key, src_val in source_data.items():
            if not isinstance(src_val, str):
                continue
            val = data.get(key)
            # Only cache if it looks like a real translation (different from source)
            if isinstance(val, str) and val != src_val:
                lang_cache[key] = val

    return cache

def safe_translate_with_timeout(
    translator: Translator,
    text: str,
    timeout_seconds: float,
    control_state,
) -> str:
    """
    Call translator.translate(text) but enforce a hard wall-clock timeout
    using a worker thread.

    IMPORTANT:
      - We do NOT use the 'with ThreadPoolExecutor(...) as executor' pattern
        because its __exit__ calls shutdown(wait=True), which can block forever
        if the worker thread hangs.
      - On timeout we:
          * log the timeout
          * cancel the future (best effort)
          * shutdown with wait=False so we do NOT block on stuck threads.
    """
    if control_state.get("stop"):
        logger.debug(
            "safe_translate_with_timeout: stop flag set, raising KeyboardInterrupt"
        )
        raise KeyboardInterrupt()

    text_str = text if isinstance(text, str) else str(text)
    text_preview = text_str.strip().replace("\n", " ")[:80]

    logger.debug(
        "safe_translate_with_timeout: START len=%d timeout=%.1fs text=%r",
        len(text_str),
        timeout_seconds,
        text_preview,
    )

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(translator.translate, text)
    timed_out = False

    try:
        result = future.result(timeout=timeout_seconds)

        if isinstance(result, str):
            res_preview = result.strip().replace("\n", " ")[:80]
            res_len = len(result)
        else:
            res_preview = "<non-str>"
            res_len = -1

        logger.debug(
            "safe_translate_with_timeout: SUCCESS len=%d text=%r",
            res_len,
            res_preview,
        )
        return result

    except FuturesTimeoutError:
        timed_out = True
        logger.error(
            "safe_translate_with_timeout: TIMEOUT after %.1fs for text=%r",
            timeout_seconds,
            text_preview,
        )
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise TimeoutError(
            f"Translation call exceeded {timeout_seconds:.1f}s timeout"
        )

    except Exception as e:
        logger.exception(
            "safe_translate_with_timeout: EXCEPTION %s for text=%r",
            type(e).__name__,
            text_preview,
        )
        raise

    finally:
        if not timed_out:
            try:
                executor.shutdown(wait=True, cancel_futures=True)
            except Exception:
                logger.debug(
                    "safe_translate_with_timeout: exception during executor.shutdown "
                    "(ignored)",
                    exc_info=True,
                )

def translate_text(
    key: str,
    text: str,
    target_language: str,
    translator: Translator,
    rate_state,
    rate_lock,
    lang_key_cache,
    control_state,
) -> str:
    """
    Translate a single string with:
      - Per-language+key cache
      - Global rate limiting across all processes
      - Hard timeout per provider call (so VPN / network issues can't hang us)
      - Finite retry for transient errors
      - Cooperative cancellation via control_state["stop"]
      - Detailed debug logging to a file
    """
    text_str = text if isinstance(text, str) else str(text)
    text_preview = text_str.strip().replace("\n", " ")[:80]

    logger.debug(
        "translate_text: START lang=%s key=%s len=%d text=%r",
        target_language,
        key,
        len(text_str),
        text_preview,
    )

    # --- 0) Cache lookup (language+key) ---
    lang_cache = lang_key_cache.get(target_language)
    if lang_cache is not None and key in lang_cache:
        logger.debug(
            "translate_text: CACHE HIT lang=%s key=%s", target_language, key
        )
        return lang_cache[key]

    # Nothing to do for empty / whitespace strings
    if not text or text_str.strip() == "":
        logger.debug(
            "translate_text: EMPTY text, lang=%s key=%s", target_language, key
        )
        return text

    # Errors that mean "this will never work for this key/language"
    FATAL_SUBSTRINGS = [
        "generator raised StopIteration",
        "unsupported language",
        "invalid target language",
        "BAD_REQUEST",
        "NEXT AVAILABLE IN",  # MyMemory hard limit message
    ]

    def store_and_return(original: str) -> str:
        """Helper to write the fallback value into the cache and return it."""
        current_cache = lang_key_cache.get(target_language) or {}
        current_cache[key] = original
        lang_key_cache[target_language] = current_cache
        logger.debug(
            "translate_text: store_and_return lang=%s key=%s value_preview=%r",
            target_language,
            key,
            (original.strip().replace("\n", " ")[:80] if isinstance(original, str) else "<non-str>"),
        )
        return original

    for attempt in range(1, MAX_TRANSIENT_ATTEMPTS + 1):
        if control_state.get("stop"):
            logger.info(
                "translate_text: stop flag set, lang=%s key=%s attempt=%d",
                target_language,
                key,
                attempt,
            )
            raise KeyboardInterrupt()

        logger.debug(
            "translate_text: ATTEMPT %d lang=%s key=%s",
            attempt,
            target_language,
            key,
        )

        try:
            # --- 1) Global rate limit (throttle across all workers) ---
            with rate_lock:
                now = time.time()
                last = rate_state.get("last_request_time", 0.0)
                min_interval = 1.0 / REQUESTS_PER_SECOND
                elapsed = now - last
                sleep_needed = min_interval - elapsed
                if sleep_needed > 0:
                    logger.debug(
                        "translate_text: rate-limit sleep %.3fs (elapsed=%.3f) "
                        "lang=%s key=%s",
                        sleep_needed,
                        elapsed,
                        target_language,
                        key,
                    )
                    cooperative_sleep(sleep_needed, control_state)

                # Reserve this slot
                rate_state["last_request_time"] = time.time()

            # --- 2) Actual translation with a HARD timeout ---
            result = safe_translate_with_timeout(
                translator=translator,
                text=text_str,
                timeout_seconds=TRANSLATE_CALL_TIMEOUT_SECONDS,
                control_state=control_state,
            )

            if result is None or not isinstance(result, str):
                logger.warning(
                    "translate_text: non-string or None result, lang=%s key=%s "
                    "result=%r; keeping original text.",
                    target_language,
                    key,
                    result,
                )
                return store_and_return(text_str)

            logger.info(
                "translate_text: SUCCESS lang=%s key=%s attempt=%d",
                target_language,
                key,
                attempt,
            )
            return store_and_return(result)

        except KeyboardInterrupt:
            logger.info(
                "translate_text: KeyboardInterrupt lang=%s key=%s attempt=%d",
                target_language,
                key,
                attempt,
            )
            raise

        except Exception as e:
            msg = str(e)
            logger.warning(
                "translate_text: EXCEPTION lang=%s key=%s attempt=%d error=%r",
                target_language,
                key,
                attempt,
                msg,
            )

            tqdm.write(
                f"[Core {os.getpid()}] Warning: Translation failed "
                f"(Attempt {attempt}) for language {target_language}, key '{key}'. "
                f"Error: {msg}"
            )

            # === Classify failure ===
            # Hard timeout: treat as fatal – don't sit here retrying forever.
            is_timeout = isinstance(e, TimeoutError) or "timed out" in msg.lower()

            fatal = is_timeout or any(sub in msg for sub in FATAL_SUBSTRINGS)

            transient = (
                (not fatal)
                and (
                    "429" in msg
                    or "Too Many Requests" in msg
                    or "RemoteDisconnected" in msg
                    or "connection aborted" in msg.lower()
                    or "temporary failure" in msg.lower()
                )
            )

            if fatal or not transient:
                # Non-retriable: provider bug, unsupported language,
                # hard timeout, or some weird error that isn't clearly transient.
                logger.error(
                    "translate_text: FATAL (or non-transient) error lang=%s key=%s "
                    "error=%r; keeping original text.",
                    target_language,
                    key,
                    msg,
                )
                tqdm.write(
                    f"[Core {os.getpid()}] Non-transient/fatal error for "
                    f"language {target_language}, key '{key}'. "
                    f"Keeping original text."
                )
                return store_and_return(text_str)

            # At this point we believe it's transient (e.g. rate limit).
            if attempt < MAX_TRANSIENT_ATTEMPTS:
                backoff = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                if backoff > MAX_BACKOFF_SECONDS:
                    backoff = MAX_BACKOFF_SECONDS

                logger.warning(
                    "translate_text: TRANSIENT error lang=%s key=%s attempt=%d "
                    "backoff=%.1fs error=%r",
                    target_language,
                    key,
                    attempt,
                    backoff,
                    msg,
                )

                tqdm.write(
                    f"[Core {os.getpid()}] Transient error ({target_language}, "
                    f"key '{key}'). Backing off for {backoff:.1f}s before retry..."
                )
                cooperative_sleep(backoff, control_state)
                continue

            # Too many transient attempts: give up for this key+language.
            logger.error(
                "translate_text: GIVING UP lang=%s key=%s after %d attempts; "
                "keeping original text.",
                target_language,
                key,
                MAX_TRANSIENT_ATTEMPTS,
            )
            tqdm.write(
                f"[Core {os.getpid()}] Giving up on language {target_language}, "
                f"key '{key}' after {MAX_TRANSIENT_ATTEMPTS} attempts. "
                f"Leaving original text unchanged."
            )
            return store_and_return(text_str)

def process_translation_file(
    filename: str,
    source_data: dict,
    translations_dir: str,
    rate_state,
    rate_lock,
    lang_key_cache,
    control_state,
) -> str:
    """
    Worker function executed by each process in the Pool.

    Behaviour:
      - Uses .done markers so completed files are not reprocessed.
      - For English locales (en_*), clones en_GB.json and never calls the translator.
      - For other locales:
          * Resolves an *effective* language via LANGUAGE_FALLBACKS, e.g.:
                raw_language 'kl' -> effective_language 'da'
          * Uses the effective language for:
                - Translation
                - Caching (lang_key_cache)
                - Reference-file reuse
      - Logs per-core progress and clearly indicates when a fallback language
        is being used for a given locale.
      - Writes detailed debug info into batch_translator_debug.log
    """
    if control_state.get("stop"):
        logger.info(
            "process_translation_file: stop flag set at entry, file=%s pid=%d",
            filename,
            os.getpid(),
        )
        raise KeyboardInterrupt()

    file_path = os.path.join(translations_dir, filename)
    raw_language = get_target_language(file_path)  # e.g. 'kl' from 'kl_GL.json'
    effective_language, is_fallback = resolve_effective_language(raw_language)
    done_marker = file_path + DONE_SUFFIX
    total_keys = len(source_data)

    logger.info(
        "process_translation_file: START file=%s raw=%s effective=%s total_keys=%d pid=%d",
        filename,
        raw_language,
        effective_language,
        total_keys,
        os.getpid(),
    )

    # 1) If this file has already been processed, skip it.
    if os.path.exists(done_marker):
        tqdm.write(f"[Skip] {filename} already has a .done marker. Skipping.")
        logger.info(
            "process_translation_file: SKIP existing .done file=%s", filename
        )
        return filename

    # Log when we are using a fallback language for this locale
    if is_fallback:
        msg = (
            f"[Fallback] {filename}: locale language '{raw_language}' is not "
            f"supported or is configured to fallback — using '{effective_language}' "
            f"for translation."
        )
        tqdm.write(msg)
        logger.info(
            "process_translation_file: FALLBACK file=%s raw=%s effective=%s",
            filename,
            raw_language,
            effective_language,
        )

    # 2) Special case: all English locales should be direct clones of en_GB.json.
    #    Here we care about the *raw* locale language.
    if raw_language == "en":
        tqdm.write(
            f"[EN CLONE][Core {os.getpid()}] {filename}: copying from en_GB.json "
            f"(no translation)."
        )
        logger.info(
            "process_translation_file: EN_CLONE file=%s from=en_GB.json", filename
        )
        en_gb_path = os.path.join(translations_dir, "en_GB.json")

        try:
            with open(en_gb_path, "r", encoding="utf-8") as f_source:
                en_gb_data = json.load(f_source)

            # Write the cloned data into this locale file
            with open(file_path, "w", encoding="utf-8") as f_target:
                json.dump(en_gb_data, f_target, ensure_ascii=False, indent=4)

            # Mark as done so we never touch it again
            with open(done_marker, "w", encoding="utf-8") as f_done:
                f_done.write("ok\n")

        except Exception as e:
            tqdm.write(
                f"[Core {os.getpid()}] ERROR: Failed to clone en_GB.json "
                f"into {filename}: {e}"
            )
            logger.exception(
                "process_translation_file: ERROR cloning en_GB.json into %s: %s",
                filename,
                e,
            )

        return filename

    # 3) For non-English locales: see if we can clone from an existing reference.
    #    A "reference" is any other file in translations_dir with:
    #      - same *effective* language (after fallback), and
    #      - its own .done marker present.
    reference_path = None
    try:
        for other_fname in os.listdir(translations_dir):
            if not other_fname.endswith(".json"):
                continue

            other_path = os.path.join(translations_dir, other_fname)
            if other_path == file_path:
                continue  # don't use self as reference

            other_raw_lang = get_target_language(other_path)
            other_effective_lang, _ = resolve_effective_language(other_raw_lang)

            if other_effective_lang != effective_language:
                continue

            other_done = other_path + DONE_SUFFIX
            if os.path.exists(other_done):
                reference_path = other_path
                break
    except Exception as e:
        tqdm.write(
            f"[Core {os.getpid()}] Warning: failed scanning for reference for "
            f"{filename} (locale '{raw_language}', effective '{effective_language}'): {e}"
        )
        logger.exception(
            "process_translation_file: ERROR scanning for reference file=%s raw=%s effective=%s",
            filename,
            raw_language,
            effective_language,
        )

    if reference_path is not None:
        ref_name = os.path.basename(reference_path)
        tqdm.write(
            f"[LANG CLONE][Core {os.getpid()}] {filename}: copying from reference "
            f"{ref_name} for effective language '{effective_language}' "
            f"(locale language '{raw_language}')."
        )
        logger.info(
            "process_translation_file: LANG_CLONE file=%s from=%s effective=%s raw=%s",
            filename,
            ref_name,
            effective_language,
            raw_language,
        )
        try:
            with open(reference_path, "r", encoding="utf-8") as f_src:
                ref_data = json.load(f_src)

            with open(file_path, "w", encoding="utf-8") as f_dst:
                json.dump(ref_data, f_dst, ensure_ascii=False, indent=4)

            with open(done_marker, "w", encoding="utf-8") as f_done:
                f_done.write("ok\n")

        except Exception as e:
            tqdm.write(
                f"[Core {os.getpid()}] ERROR: Failed cloning {ref_name} into "
                f"{filename}: {e}"
            )
            logger.exception(
                "process_translation_file: ERROR cloning reference %s into %s: %s",
                ref_name,
                filename,
                e,
            )

        return filename

    # 4) No existing reference for this effective language: this file becomes
    #    the reference for that effective language.
    tqdm.write(
        f"Starting translation of {filename} "
        f"(locale '{raw_language}', effective '{effective_language}') "
        f"on Core {os.getpid()} with {total_keys} keys..."
    )
    logger.info(
        "process_translation_file: TRANSLATE file=%s raw=%s effective=%s total_keys=%d",
        filename,
        raw_language,
        effective_language,
        total_keys,
    )

    # Load existing translation data (if any)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            target_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        target_data = {}

    # Quick check: do we actually need work in this file?
    work_needed = False
    for key, value in source_data.items():
        if isinstance(value, str):
            existing = target_data.get(key)
            # If any string key is missing or still equal to the source, we have work.
            if not existing or existing == value:
                work_needed = True
                break

    if not work_needed:
        tqdm.write(
            f"[Skip][Core {os.getpid()}] {filename} is already fully translated. Skipping."
        )
        logger.info(
            "process_translation_file: NO_WORK file=%s raw=%s effective=%s",
            filename,
            raw_language,
            effective_language,
        )
        # Even if we didn't translate it just now, it can serve as a reference.
        try:
            with open(done_marker, "w", encoding="utf-8") as f_done:
                f_done.write("ok\n")
        except Exception as e:
            tqdm.write(
                f"[Core {os.getpid()}] Warning: could not write .done marker "
                f"for {filename}: {e}"
            )
            logger.warning(
                "process_translation_file: WARNING could not write .done marker "
                "for file=%s: %s",
                filename,
                e,
            )
        return filename

    # Initialize translator for this worker using the *effective* language
    try:
        translator = Translator(
            to_lang=effective_language,
            from_lang="en",
            service_urls=[
                "translate.google.com",
                "translate.google.co.kr",
                "translate.google.co.jp",
            ],
        )
    except Exception as e:
        tqdm.write(
            f"[Core {os.getpid()}] ERROR: Failed to initialize Translator "
            f"for effective language '{effective_language}' "
            f"(locale language '{raw_language}') in {filename}: {e}"
        )
        logger.exception(
            "process_translation_file: ERROR initializing Translator file=%s "
            "raw=%s effective=%s: %s",
            filename,
            raw_language,
            effective_language,
            e,
        )
        return filename

    logger.info(
        "process_translation_file: TRANSLATOR_READY file=%s effective=%s",
        filename,
        effective_language,
    )

    translated_count = 0

    for key, value in source_data.items():
        if control_state.get("stop"):
            logger.info(
                "process_translation_file: stop flag during loop file=%s key=%s",
                filename,
                key,
            )
            raise KeyboardInterrupt()

        if isinstance(value, str):
            existing = target_data.get(key)

            # If there's already a translated value, keep it and cache it.
            if existing and existing != value:
                translated = existing
                current_cache = lang_key_cache.get(effective_language) or {}
                current_cache[key] = translated
                lang_key_cache[effective_language] = current_cache
                logger.debug(
                    "process_translation_file: REUSE_EXISTING file=%s key=%s "
                    "effective=%s",
                    filename,
                    key,
                    effective_language,
                )
            else:
                logger.debug(
                    "process_translation_file: TRANSLATE key=%s file=%s effective=%s",
                    key,
                    filename,
                    effective_language,
                )
                translated = translate_text(
                    key,
                    value,
                    effective_language,  # cache/log under effective language
                    translator,
                    rate_state,
                    rate_lock,
                    lang_key_cache,
                    control_state,
                )

            target_data[key] = translated
        else:
            # Non-string values are copied as-is.
            target_data[key] = value

        translated_count += 1

        # Per-core progress logging (keys, not files)
        if translated_count % 100 == 0 or translated_count == total_keys:
            percent = (
                100.0 if total_keys == 0 else (translated_count * 100.0 / total_keys)
            )
            tqdm.write(
                f"[Core {os.getpid()}] {filename}: "
                f"{translated_count}/{total_keys} keys ({percent:.1f}%) done."
            )
            logger.debug(
                "process_translation_file: PROGRESS file=%s keys=%d/%d (%.1f%%)",
                filename,
                translated_count,
                total_keys,
                percent,
            )

    # Write the resulting translated data back to the file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(target_data, f, ensure_ascii=False, indent=4)

    # Mark this file as the completed reference for this effective language
    try:
        with open(done_marker, "w", encoding="utf-8") as f_done:
            f_done.write("ok\n")
    except Exception as e:
        tqdm.write(
            f"[Core {os.getpid()}] Warning: could not write .done marker "
            f"for {filename}: {e}"
        )
        logger.warning(
            "process_translation_file: WARNING could not write .done marker "
            "for file=%s: %s",
            filename,
            e,
        )

    tqdm.write(
        f"Finished translation of {filename} on Core {os.getpid()} "
        f"(locale '{raw_language}', effective '{effective_language}')."
    )
    logger.info(
        "process_translation_file: DONE file=%s raw=%s effective=%s keys=%d",
        filename,
        raw_language,
        effective_language,
        translated_count,
    )
    return filename


def main():
    """Main function to parallelize the translation across multiple processes.

    Progress indication:
      - `tqdm` shows an overall progress bar over files.
      - After each file completes, we log:
        [Overall] A/B files complete (C.C%) using MAX_PROCESSES cores.
    """

    tqdm.write("Free MyMemory/Translate client ready.")

    base_dir = os.path.dirname(__file__)
    translations_dir = os.path.join(base_dir, "localization", "translations")
    source_file = os.path.join(translations_dir, "en_GB.json")  # source only

    # Load source data
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            source_data = json.load(f)
        tqdm.write(f"Loading source data from: {source_file}")
    except FileNotFoundError:
        tqdm.write(f"Error: Source file not found at {source_file}")
        return

    # Files to translate
    files_to_translate = [
        f
        for f in os.listdir(translations_dir)
        if f.endswith(".json") and f not in ["en_GB.json", "key_reference.json"]
    ]

    total_files = len(files_to_translate)

    tqdm.write(
        f"--- Found {total_files} files to translate. "
        f"Using {MAX_PROCESSES} concurrent processes on {CPU_COUNT} available cores. ---"
    )

    if not files_to_translate:
        tqdm.write("No translation files to process.")
        return

    # Initial cache from existing translations
    initial_cache = init_language_key_cache(translations_dir, source_data)
    tqdm.write(
        f"Initialized language cache for {len(initial_cache)} language(s) "
        f"from existing translation files."
    )

    manager = multiprocessing.Manager()
    rate_state = manager.dict()
    rate_state["last_request_time"] = 0.0
    rate_lock = manager.Lock()

    lang_key_cache = manager.dict()
    for lang, mapping in initial_cache.items():
        lang_key_cache[lang] = dict(mapping)

    control_state = manager.dict()
    control_state["stop"] = False  # set to True on Ctrl+C

    worker = functools.partial(
        process_translation_file,
        source_data=source_data,
        translations_dir=translations_dir,
        rate_state=rate_state,
        rate_lock=rate_lock,
        lang_key_cache=lang_key_cache,
        control_state=control_state,
    )

    pool = multiprocessing.Pool(processes=MAX_PROCESSES)

    completed_files = 0

    try:
        for _ in tqdm(
            pool.imap_unordered(worker, files_to_translate),
            total=total_files,
            desc="Overall File Translation Progress",
            unit="file",
            dynamic_ncols=True,
        ):
            if control_state.get("stop"):
                break

            # --- OVERALL PROGRESS REPORTING ---
            completed_files += 1
            overall_pct = 100.0 if total_files == 0 else (completed_files * 100.0 / total_files)
            tqdm.write(
                f"[Overall] {completed_files}/{total_files} files complete "
                f"({overall_pct:.1f}%) using up to {MAX_PROCESSES} cores."
            )
            # -----------------------------------

        pool.close()
        pool.join()
        tqdm.write("\nAll translation files processed (or cancelled).")

    except KeyboardInterrupt:
        tqdm.write("\nCtrl+C detected: requesting graceful shutdown...")
        control_state["stop"] = True
        pool.terminate()
        pool.join()
        tqdm.write("All worker processes terminated due to Ctrl+C.")

    except Exception as e:
        tqdm.write(f"An error occurred during multiprocessing: {e}")
        control_state["stop"] = True
        pool.terminate()
        pool.join()
        # Don't re-raise: we want a clean exit
        # If you prefer to see the traceback, you could 'raise' here instead.


if __name__ == "__main__":
    multiprocessing.freeze_support()  # for Windows
    main()
