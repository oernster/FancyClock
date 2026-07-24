"""Shared UI colours: one accent, defined once.

The amber accent replaces the native light-blue highlight, which has
poor contrast under white text. Anything painted on the accent uses
``ON_ACCENT`` (near-black), never white.
"""

from __future__ import annotations

ACCENT = "#F59E0B"
ON_ACCENT = "#101319"
PANEL = "#1d2230"
PANEL_BORDER = "#3a4356"
TEXT = "#e8ecf4"
TEXT_MUTED = "#8b93a7"
