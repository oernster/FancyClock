"""
Thin client around a local LibreTranslate instance.

Assumes:
- Server is running at http://localhost:5000 (configurable).
- No API key required (default LibreTranslate docker behaviour).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import requests


LOG = logging.getLogger("libretranslate_client")


@dataclass
class LibreTranslateClient:
    base_url: str = "http://localhost:5000"
    timeout: int = 30
    max_retries: int = 4
    backoff_initial: float = 0.5
    session: requests.Session = field(default_factory=requests.Session, init=False)
    _supported_langs_cache: Dict[str, dict] = field(default_factory=dict, init=False)

    @property
    def translate_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/translate"

    @property
    def languages_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/languages"

    # -------------------------------
    # Language discovery
    # -------------------------------
    def get_supported_languages(self) -> Dict[str, dict]:
        """
        Return mapping of language code -> metadata from /languages.
        Caches results for subsequent calls.
        """
        if self._supported_langs_cache:
            return self._supported_langs_cache

        LOG.info("Fetching supported languages from LibreTranslate...")
        resp = self.session.get(self.languages_url, timeout=self.timeout)
        resp.raise_for_status()
        langs = resp.json()

        self._supported_langs_cache = {entry["code"]: entry for entry in langs}
        LOG.info(
            "LibreTranslate supports %d languages: %s",
            len(self._supported_langs_cache),
            ", ".join(sorted(self._supported_langs_cache.keys())),
        )
        return self._supported_langs_cache

    def get_supported_codes(self) -> set[str]:
        return set(self.get_supported_languages().keys())

    # -------------------------------
    # Translation
    # -------------------------------
    def translate_batch(
        self,
        texts: Sequence[str],
        source_lang: str,
        target_lang: str,
    ) -> List[str]:
        """
        Translate a list of strings from source_lang to target_lang using a single request.

        LibreTranslate supports multiple values for 'q', returning a list of translated strings.
        """
        if not texts:
            return []

        payload = {
            "q": list(texts),
            "source": source_lang,
            "target": target_lang,
            "format": "text",
        }

        backoff = self.backoff_initial
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.post(
                    self.translate_url,
                    data=payload,
                    timeout=self.timeout,
                )
                if resp.status_code >= 500:
                    raise RuntimeError(
                        f"Server error {resp.status_code}: {resp.text[:200]}"
                    )
                resp.raise_for_status()

                data = resp.json()

                # When 'q' is a list, LibreTranslate returns list-of-dicts
                # [{'translatedText': '...'}, ...].
                if isinstance(data, list):
                    return [item["translatedText"] for item in data]

                # Fallback: single translation response
                if isinstance(data, dict) and "translatedText" in data:
                    return [data["translatedText"]]

                raise RuntimeError(f"Unexpected response format: {json.dumps(data)[:200]}")

            except Exception as exc:  # noqa: BLE001
                last_exception = exc
                LOG.warning(
                    "Translate attempt %d/%d failed (%s). Retrying in %.2fs",
                    attempt,
                    self.max_retries,
                    exc,
                    backoff,
                )
                time.sleep(backoff)
                backoff *= 2.0

        raise RuntimeError(
            f"Translation failed after {self.max_retries} attempts"
        ) from last_exception
