"""JsonSettingsStore tests against a real temp directory."""

from __future__ import annotations

import json

from fancyclock.infrastructure.json_settings_store import (
    APP_NAME,
    SETTINGS_FILE_NAME,
    JsonSettingsStore,
    default_config_dir,
)


def test_set_and_get_roundtrip(tmp_path) -> None:
    store = JsonSettingsStore(config_dir=tmp_path)
    store.set("example", 123)

    data = json.loads((tmp_path / SETTINGS_FILE_NAME).read_text("utf-8"))
    assert data["example"] == 123
    assert store.get("example") == 123


def test_get_missing_returns_default(tmp_path) -> None:
    store = JsonSettingsStore(config_dir=tmp_path)
    assert store.get("missing") is None
    assert store.get("missing", "fallback") == "fallback"


def test_set_none_removes_key(tmp_path) -> None:
    store = JsonSettingsStore(config_dir=tmp_path)
    store.set("a", 1)
    store.set("b", 2)
    store.set("a", None)

    data = json.loads((tmp_path / SETTINGS_FILE_NAME).read_text("utf-8"))
    assert "a" not in data
    assert data["b"] == 2


def test_broken_json_is_ignored(tmp_path) -> None:
    (tmp_path / SETTINGS_FILE_NAME).write_text("{not json", encoding="utf-8")
    store = JsonSettingsStore(config_dir=tmp_path)
    assert store.get("anything") is None


def test_non_dict_json_is_ignored(tmp_path) -> None:
    (tmp_path / SETTINGS_FILE_NAME).write_text("[1, 2]", encoding="utf-8")
    store = JsonSettingsStore(config_dir=tmp_path)
    assert store.get("anything") is None


def test_settings_path_creates_directory(tmp_path) -> None:
    nested = tmp_path / "nested" / "dir"
    store = JsonSettingsStore(config_dir=nested)
    path = store.settings_path()
    assert nested.is_dir()
    assert path.name == SETTINGS_FILE_NAME


def test_default_config_dir_ends_with_app_name() -> None:
    assert default_config_dir().name == APP_NAME


def test_default_ctor_uses_default_dir() -> None:
    store = JsonSettingsStore()
    assert store._config_dir == default_config_dir()
