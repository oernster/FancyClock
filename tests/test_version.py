"""Version module tests."""

from __future__ import annotations

import sys
from pathlib import Path

from fancyclock.version import (
    FALLBACK_VERSION,
    VERSION_FILENAME,
    __version__,
    _candidate_dirs,
    read_version,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dunder_version_matches_version_file() -> None:
    canonical = (PROJECT_ROOT / VERSION_FILENAME).read_text("utf-8").strip()
    assert __version__ == canonical


def test_read_version_from_explicit_dir(tmp_path) -> None:
    (tmp_path / VERSION_FILENAME).write_text("9.9.9\n", encoding="utf-8")
    assert read_version((tmp_path,)) == "9.9.9"


def test_read_version_skips_empty_file(tmp_path) -> None:
    (tmp_path / VERSION_FILENAME).write_text("  \n", encoding="utf-8")
    assert read_version((tmp_path,)) == FALLBACK_VERSION


def test_read_version_missing_returns_fallback(tmp_path) -> None:
    assert read_version((tmp_path,)) == FALLBACK_VERSION


def test_candidate_dirs_without_meipass(monkeypatch) -> None:
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    dirs = _candidate_dirs()
    assert PROJECT_ROOT in dirs


def test_candidate_dirs_with_meipass(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert _candidate_dirs()[0] == tmp_path
