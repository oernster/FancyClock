"""Pure rules for video skin discovery and naming."""

from __future__ import annotations

SKIN_FILE_SUFFIX = ".mp4"
DEFAULT_SKIN_STEM = "mesmerize"


def is_skin_filename(filename: str) -> bool:
    """Return True when the filename is a video skin file."""
    return filename.lower().endswith(SKIN_FILE_SUFFIX)


def skin_stem(filename: str) -> str:
    """Return the skin name (filename without its suffix)."""
    if is_skin_filename(filename):
        return filename[: -len(SKIN_FILE_SUFFIX)]
    return filename


def skin_display_name(filename: str) -> str:
    """Return the human-readable skin name shown in the menu."""
    return skin_stem(filename).replace("_", " ").title()
