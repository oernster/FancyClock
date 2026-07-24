"""Resource-resolution tests across dev and frozen modes."""

from __future__ import annotations

import os
import sys

from fancyclock.infrastructure.resources import (
    APP_ICON_ICO,
    APP_ICON_PNG_256,
    ASSETS_DIR_NAME,
    find_license_file,
    get_about_icon_path,
    get_app_icon_path,
    resource_path,
)


def test_resource_path_in_dev_mode_uses_cwd(tmp_path, monkeypatch) -> None:
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.chdir(tmp_path)
    assert resource_path("foo.txt") == os.path.join(str(tmp_path), "foo.txt")


def test_resource_path_in_frozen_mode_uses_meipass(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_path("foo.txt") == os.path.join(str(tmp_path), "foo.txt")


def test_find_license_file_prefers_plain_license(tmp_path, monkeypatch) -> None:
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.chdir(tmp_path)
    assert find_license_file() is None

    (tmp_path / "LICENSE.txt").write_text("txt", encoding="utf-8")
    assert find_license_file().endswith("LICENSE.txt")

    (tmp_path / "LICENSE").write_text("plain", encoding="utf-8")
    assert find_license_file().endswith("LICENSE")


def test_app_icon_prefers_ico_with_png_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.chdir(tmp_path)

    assert get_app_icon_path().endswith(APP_ICON_PNG_256)

    assets = tmp_path / ASSETS_DIR_NAME
    assets.mkdir()
    (assets / APP_ICON_ICO).write_bytes(b"")
    assert get_app_icon_path().endswith(APP_ICON_ICO)


def test_about_icon_path_points_into_assets(tmp_path, monkeypatch) -> None:
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.chdir(tmp_path)
    path = get_about_icon_path()
    assert ASSETS_DIR_NAME in path
    assert path.endswith(APP_ICON_PNG_256)
