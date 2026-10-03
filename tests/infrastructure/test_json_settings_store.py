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


def test_a_damaged_file_is_kept_aside_before_the_first_save(tmp_path) -> None:
    path = tmp_path / SETTINGS_FILE_NAME
    path.write_text('{"timezone": "Europe/Paris", "skin": "wav', encoding="utf-8")
    damaged = path.read_bytes()
    store = JsonSettingsStore(config_dir=tmp_path)

    store.set("alarm_volume", 0.3)

    kept = tmp_path / "settings.damaged-1.json"
    assert kept.read_bytes() == damaged
    assert json.loads(path.read_text("utf-8")) == {"alarm_volume": 0.3}


def test_a_second_damage_keeps_the_first_copy(tmp_path) -> None:
    path = tmp_path / SETTINGS_FILE_NAME
    store = JsonSettingsStore(config_dir=tmp_path)
    path.write_text("first", encoding="utf-8")
    store.set("a", 1)
    path.write_text("[2]", encoding="utf-8")
    store.set("b", 2)

    assert (tmp_path / "settings.damaged-1.json").read_text("utf-8") == "first"
    assert (tmp_path / "settings.damaged-2.json").read_text("utf-8") == "[2]"


def test_a_clean_or_missing_file_is_never_copied(tmp_path) -> None:
    store = JsonSettingsStore(config_dir=tmp_path)
    store.set("a", 1)
    store.set("b", 2)
    assert sorted(p.name for p in tmp_path.iterdir()) == [SETTINGS_FILE_NAME]


def test_a_failed_copy_refuses_the_save_so_the_original_stays(tmp_path) -> None:
    def refuse_copy(source, target) -> None:
        raise PermissionError(f"cannot copy {source} to {target}")

    path = tmp_path / SETTINGS_FILE_NAME
    path.write_text("damaged", encoding="utf-8")
    store = JsonSettingsStore(config_dir=tmp_path, copy_file=refuse_copy)

    store.set("a", 1)

    assert path.read_text("utf-8") == "damaged"
