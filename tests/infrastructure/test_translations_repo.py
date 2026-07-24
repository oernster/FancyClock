"""JsonTranslationsRepository tests against real temp files."""

from __future__ import annotations

import json

from fancyclock.infrastructure.translations_repo import JsonTranslationsRepository


def test_loads_full_locale_file(tmp_path) -> None:
    (tmp_path / "fr_FR.json").write_text(json.dumps({"help": "Aide"}), encoding="utf-8")
    repo = JsonTranslationsRepository(tmp_path)
    assert repo.load("fr_FR") == {"help": "Aide"}


def test_falls_back_to_language_file(tmp_path) -> None:
    (tmp_path / "fr.json").write_text(json.dumps({"help": "Aide"}), encoding="utf-8")
    repo = JsonTranslationsRepository(tmp_path)
    assert repo.load("fr_FR") == {"help": "Aide"}


def test_missing_locale_returns_none(tmp_path) -> None:
    repo = JsonTranslationsRepository(tmp_path)
    assert repo.load("de_DE") is None


def test_invalid_json_returns_none(tmp_path) -> None:
    (tmp_path / "de_DE.json").write_text("{broken", encoding="utf-8")
    repo = JsonTranslationsRepository(tmp_path)
    assert repo.load("de_DE") is None


def test_non_dict_json_returns_none(tmp_path) -> None:
    (tmp_path / "de_DE.json").write_text("[1]", encoding="utf-8")
    repo = JsonTranslationsRepository(tmp_path)
    assert repo.load("de_DE") is None
