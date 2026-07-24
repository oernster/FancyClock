"""Clock window animation mixin."""

from __future__ import annotations


class WindowAnimationMixin:
    """Adds the high-frequency animation loop helper methods."""

    def update_animation(self) -> None:
        """Slot called by the animation timer roughly 60 times per second."""
        self.analog_clock.animate()
        self.digital_clock.animate()
