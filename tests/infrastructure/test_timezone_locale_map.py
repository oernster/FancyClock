"""JsonTimezoneLocaleMap tests against real temp files."""

from __future__ import annotations

import json

from fancyclock.infrastructure.timezone_locale_map import JsonTimezoneLocaleMap

MAPPING = {"Europe/London": "en_GB", "Europe/Paris": "fr_FR"}


def _map_file(tmp_path, content: str):
    path = tmp_path / "timezone_locale_map.json"
    path.write_text(content, encoding="utf-8")
    return path


def test_lookup_hit_and_miss(tmp_path) -> None:
    tz_map = JsonTimezoneLocaleMap(_map_file(tmp_path, json.dumps(MAPPING)))
    assert tz_map.locale_for("Europe/Paris") == "fr_FR"
    assert tz_map.locale_for("Atlantis/Nowhere") is None


def test_none_uses_injected_system_zone(tmp_path) -> None:
    tz_map = JsonTimezoneLocaleMap(
        _map_file(tmp_path, json.dumps(MAPPING)),
        localzone_name=lambda: "Europe/London",
    )
    assert tz_map.locale_for(None) == "en_GB"


def test_system_zone_failure_returns_none(tmp_path) -> None:
    def broken() -> str:
        raise RuntimeError("no zone")

    tz_map = JsonTimezoneLocaleMap(
        _map_file(tmp_path, json.dumps(MAPPING)), localzone_name=broken
    )
    assert tz_map.locale_for(None) is None


def test_broken_map_file_yields_empty_map(tmp_path) -> None:
    tz_map = JsonTimezoneLocaleMap(_map_file(tmp_path, "{broken"))
    assert tz_map.locale_for("Europe/London") is None


def test_non_dict_map_file_yields_empty_map(tmp_path) -> None:
    tz_map = JsonTimezoneLocaleMap(_map_file(tmp_path, "[1]"))
    assert tz_map.locale_for("Europe/London") is None
