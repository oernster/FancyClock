"""Clock window opacity probing mixin."""

from __future__ import annotations

import os
import sys


class WindowOpacityMixin:
    """Detect platform support for window opacity."""

    def _supports_window_opacity(self) -> bool:
        """Return True if opacity can be set without platform plugin errors."""
        if os.environ.get("FLATPAK_ID") and sys.platform.startswith("linux"):
            return False

        try:
            self.setWindowOpacity(0.99)
            self.setWindowOpacity(1.0)
            return True
        except Exception:
            return False
