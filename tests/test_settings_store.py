from __future__ import annotations

import json

import settings_store


def test_set_setting_writes_json_atomic(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"

    monkeypatch.setattr(settings_store, "settings_path", lambda: settings_file)

    settings_store.set_setting("example", 123)

    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert data["example"] == 123


def test_set_setting_none_removes_key(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"a": 1, "b": 2}), encoding="utf-8")

    monkeypatch.setattr(settings_store, "settings_path", lambda: settings_file)

    settings_store.set_setting("a", None)
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert "a" not in data
    assert data["b"] == 2
