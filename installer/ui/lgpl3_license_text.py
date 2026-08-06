"""GNU LGPL v3 license text for display in the installer UI."""

from __future__ import annotations

import sys
from pathlib import Path


def _read_lgpl3_text() -> str:
    """Load LGPL v3 text from repo-root `LICENSE`."""

    candidates: list[Path] = []

    # PyInstaller's extraction directory, present only in a frozen build.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "LICENSE")

    # Beside the executable, then the repository root when running from source.
    # resolve() touches the filesystem and parents[2] assumes this module's
    # depth, so a broken path or an unexpected layout drops that candidate
    # rather than the whole search.
    for build_candidate in (
        lambda: Path(sys.executable).resolve().parent / "LICENSE",
        lambda: Path(__file__).resolve().parents[2] / "LICENSE",
    ):
        try:
            candidates.append(build_candidate())
        except (OSError, IndexError):
            continue

    candidates.append(Path.cwd() / "LICENSE")

    for p in candidates:
        try:
            if p.exists() and p.is_file():
                return p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # Unreadable or on a volume that has gone away: try the next place
            # rather than failing the whole lookup.
            continue

    raise FileNotFoundError(
        "Unable to locate LICENSE. Tried: " + ", ".join(str(p) for p in candidates)
    )


LGPL_V3_TEXT = _read_lgpl3_text()
