"""Bundled-resource path resolution across dev, PyInstaller and Flatpak.

In a PyInstaller build resources live beside the unpacked bundle
(``sys._MEIPASS``); in dev and under Flatpak the working directory is the
project or app share directory, so relative lookups resolve from there.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ASSETS_DIR_NAME = "assets"
APP_ICON_ICO = "fancyclock.ico"
APP_ICON_PNG_256 = "fancyclock_icon_256.png"
ABOUT_ICON_PNG = "fancyclock_icon_256.png"
LICENSE_FILENAMES: tuple[str, ...] = ("LICENSE", "LICENSE.txt")


def resource_path(relative_path: str) -> str:
    """Return the absolute path to a bundled resource."""
    meipass = getattr(sys, "_MEIPASS", None)
    base_path = meipass if meipass else os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def find_license_file() -> str | None:
    """Return the path of the bundled licence text, or ``None``."""
    for name in LICENSE_FILENAMES:
        path = Path(resource_path(name))
        if path.is_file():
            return str(path)
    return None


def get_app_icon_path() -> str:
    """Return the window icon path, preferring the multi-size ``.ico``."""
    ico = Path(resource_path(ASSETS_DIR_NAME)) / APP_ICON_ICO
    if ico.is_file():
        return str(ico)
    return str(Path(resource_path(ASSETS_DIR_NAME)) / APP_ICON_PNG_256)


def get_about_icon_path() -> str:
    """Return the About dialog badge PNG path."""
    return str(Path(resource_path(ASSETS_DIR_NAME)) / ABOUT_ICON_PNG)
