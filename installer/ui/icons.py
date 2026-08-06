"""Qt icon helpers for installer UI."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtGui import QIcon


def build_installer_window_icon(*, project_root: Path) -> QIcon:
    """Load installer window icon from actual branded icon files."""
    from PySide6.QtGui import QIcon

    brand_path = _find_brand_icon_path(project_root=project_root)
    if brand_path is not None:
        return QIcon(str(brand_path))

    return QIcon()


def _find_brand_icon_path(*, project_root: Path) -> Path | None:
    """Find a branded icon file for the installer runtime window icon.

    Prefer PNGs (we have a known-good multi-size PNG set), then fall back to the
    `.ico` if needed.
    """

    filenames = [
        "fancyclock_icon_256.png",
        "fancyclock_icon_128.png",
        "fancyclock_icon_64.png",
        "fancyclock_icon_48.png",
        "fancyclock.ico",
    ]

    roots: list[Path] = []

    # In a frozen PyInstaller build, bundled files live under sys._MEIPASS.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))

    roots.append(project_root)

    # Beside the executable, then the working directory. Both touch the
    # filesystem, so a deleted working directory or an unresolvable executable
    # path drops that root instead of losing the icon search entirely.
    for build_root in (lambda: Path(sys.executable).resolve().parent, Path.cwd):
        try:
            roots.append(build_root())
        except OSError:
            continue

    for root in roots:
        for name in filenames:
            p = root / name
            try:
                if p.exists() and p.is_file():
                    return p
            except OSError:
                # Unreadable path or a volume that has gone away: keep looking.
                continue

    return None


def set_windows_app_user_model_id(app_id: str) -> None:
    """Set the Windows AppUserModelID for correct taskbar grouping/icon.

    This is a best-effort helper; it no-ops on non-Windows.
    """

    if os.name != "nt":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (AttributeError, OSError):
        # Taskbar grouping is cosmetic. A Windows build without the shell32
        # entry point raises AttributeError and a refused call raises OSError;
        # neither is worth failing an installation over.
        return
