"""Resolved resource paths handed to the UI by the composition root."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourcePaths:
    """Absolute paths of UI resources resolved at startup.

    ``app_icon`` is the window and taskbar icon, ``about_icon_png`` is the
    About dialog badge and ``license_file`` is the licence text shown in the
    licence dialog (``None`` when no licence file was found).
    """

    app_icon: str
    about_icon_png: str
    license_file: str | None
