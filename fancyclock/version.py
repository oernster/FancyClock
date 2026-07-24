"""Centralised version information for Fancy Clock.

The VERSION file at the repo root is the single source of truth. This module
reads it at import time; packaged builds bundle VERSION beside the executable
(PyInstaller) or in the app share directory (Flatpak), so every runtime reads
the same value. A dev sentinel is used when no VERSION file can be found.
"""

from __future__ import annotations

import sys
from pathlib import Path

VERSION_FILENAME = "VERSION"
FALLBACK_VERSION = "0.0.0-dev"

APP_NAME = "FancyClock"
APP_DISPLAY_NAME = "Fancy Clock"
APP_AUTHOR = "Oliver Ernster"
ORGANIZATION_NAME = "OliverErnster"
APP_APPUSERMODELID = "uk.codecrafter.FancyClock"


def _candidate_dirs() -> tuple[Path, ...]:
    """Directories that may hold the VERSION file, in search order."""
    dirs: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(Path(meipass))
    dirs.append(Path(__file__).resolve().parent.parent)
    dirs.append(Path.cwd())
    return tuple(dirs)


def read_version(dirs: tuple[Path, ...] | None = None) -> str:
    """Return the canonical version string, or the dev sentinel."""
    for directory in dirs if dirs is not None else _candidate_dirs():
        version_file = directory / VERSION_FILENAME
        if version_file.is_file():
            text = version_file.read_text(encoding="utf-8").strip()
            if text:
                return text
    return FALLBACK_VERSION


__version__ = read_version()
