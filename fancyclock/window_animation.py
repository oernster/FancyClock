"""Clock window animation mixin."""

from __future__ import annotations

from typing import Any


class WindowAnimationMixin:
    """Adds the high-frequency animation loop helper methods."""

    def _animate_clock(self, clock_widget: Any) -> None:
        """Advance a clock widget animation/state for the ~60 FPS loop."""
        if hasattr(clock_widget, "animate") and callable(
            getattr(clock_widget, "animate")
        ):
            try:
                clock_widget.animate()
                return
            except Exception:
                pass

        for method_name in ("update_galaxy", "update_stars", "update"):
            if hasattr(clock_widget, method_name) and callable(
                getattr(clock_widget, method_name)
            ):
                try:
                    getattr(clock_widget, method_name)()
                    return
                except Exception:
                    continue

    def update_animation(self) -> None:
        """Slot called by the animation timer roughly 60 times per second."""
        self._animate_clock(self.analog_clock)
        self._animate_clock(self.digital_clock)
