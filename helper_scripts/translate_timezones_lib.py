"""Library helpers for timezone translation.

The CLI wrapper lives in `helper_scripts/translate_timezones.py`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

import requests

LOG = logging.getLogger("translate_timezones")

SOURCE_LANG = "en"


def fetch_supported_languages(api_url: str) -> List[str]:
    url = api_url.rstrip("/") + "/languages"
    LOG.info("Fetching supported languages from LibreTranslate...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    codes = [item["code"] for item in data]
    LOG.info("LibreTranslate supports %d languages: %s", len(codes), ", ".join(codes))
    return codes


def load_json(path: Path) -> Dict[str, str]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, str]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    temp_path.replace(path)
