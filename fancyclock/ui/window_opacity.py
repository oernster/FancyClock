"""Clock window opacity probing mixin."""

from __future__ import annotations

import os
import sys

OPACITY_PROBE_VALUE = 0.99
OPACITY_OPAQUE = 1.0


class WindowOpacityMixin:
    """Detect platform support for window opacity."""

    def _supports_window_opacity(self) -> bool:
        """Return True if opacity can be set without platform plugin errors."""
        if os.environ.get("FLATPAK_ID") and sys.platform.startswith("linux"):
            return False

        try:
            self.setWindowOpacity(OPACITY_PROBE_VALUE)
            self.setWindowOpacity(OPACITY_OPAQUE)
            return True
        except Exception:
            return False
