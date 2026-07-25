"""Clock window opacity: platform probe, View-menu slider and shortcuts.

The user controls opacity three ways: the slider in the View menu,
Ctrl with the Up and Down arrows, and Ctrl with the mouse wheel. The
level persists in settings and is restored at launch (the fade-in
animation ends at the configured level). Where the platform cannot set
per-window opacity (the Flatpak sandbox) the View menu is hidden and
the shortcuts are inert.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget, QWidgetAction

OPACITY_PROBE_VALUE = 0.99
OPACITY_OPAQUE = 1.0
PERCENT_SCALE = 100
OPACITY_MIN_PERCENT = 20
OPACITY_MAX_PERCENT = 100
OPACITY_STEP_PERCENT = 5
SLIDER_WIDTH_PX = 160
SLIDER_MARGIN_PX = 10
FALLBACK_VIEW_LABEL = "View"
FALLBACK_OPACITY_LABEL = "Opacity"


class WindowOpacityMixin:
    """Opacity support probe plus the user-facing opacity control."""

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

    # ------------------------------------------------------------------
    # View menu
    # ------------------------------------------------------------------
    def _create_view_menu(self, menu_bar) -> None:
        """Build the View menu holding the opacity slider."""
        view_label = self.i18n_manager.get_translation("view")
        if view_label == "view":
            view_label = FALLBACK_VIEW_LABEL
        self.view_menu = menu_bar.addMenu(view_label)

        opacity_label = self.i18n_manager.get_translation("opacity")
        if opacity_label == "opacity":
            opacity_label = FALLBACK_OPACITY_LABEL

        container = QWidget(self)
        row = QHBoxLayout(container)
        half_margin = SLIDER_MARGIN_PX // 2
        row.setContentsMargins(
            SLIDER_MARGIN_PX, half_margin, SLIDER_MARGIN_PX, half_margin
        )
        row.addWidget(QLabel(opacity_label, container))

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal, container)
        self.opacity_slider.setRange(OPACITY_MIN_PERCENT, OPACITY_MAX_PERCENT)
        self.opacity_slider.setSingleStep(OPACITY_STEP_PERCENT)
        self.opacity_slider.setPageStep(OPACITY_STEP_PERCENT)
        self.opacity_slider.setFixedWidth(SLIDER_WIDTH_PX)
        row.addWidget(self.opacity_slider)

        self.opacity_value_label = QLabel(container)
        row.addWidget(self.opacity_value_label)

        slider_action = QWidgetAction(self)
        slider_action.setDefaultWidget(container)
        self.view_menu.addAction(slider_action)

        self.opacity_slider.setValue(self._current_opacity_percent())
        self._update_opacity_label()
        self.opacity_slider.valueChanged.connect(self._set_opacity_percent)

    # ------------------------------------------------------------------
    # Applying and persisting
    # ------------------------------------------------------------------
    def _current_opacity_percent(self) -> int:
        return round(self.settings.window_opacity() * PERCENT_SCALE)

    def _update_opacity_label(self) -> None:
        if hasattr(self, "opacity_value_label"):
            percent = self.i18n_manager.format_number(self._current_opacity_percent())
            self.opacity_value_label.setText(f"{percent}%")

    def _apply_startup_opacity(self) -> None:
        """Apply the saved level when there is no fade-in to end at it."""
        if self._opacity_supported and self.animation is None:
            self.setWindowOpacity(self.settings.window_opacity())

    def _set_opacity_percent(self, percent: int) -> None:
        """Clamp, apply, persist and reflect the new opacity."""
        if not self._opacity_supported:
            return
        clamped = max(OPACITY_MIN_PERCENT, min(OPACITY_MAX_PERCENT, int(percent)))
        self.settings.set_window_opacity(clamped / PERCENT_SCALE)
        self.setWindowOpacity(clamped / PERCENT_SCALE)
        if hasattr(self, "opacity_slider") and self.opacity_slider.value() != clamped:
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(clamped)
            self.opacity_slider.blockSignals(False)
        self._update_opacity_label()

    def _nudge_opacity(self, delta_percent: int) -> None:
        self._set_opacity_percent(self._current_opacity_percent() + delta_percent)

    # ------------------------------------------------------------------
    # Shortcut handling (delegated from the window's event overrides)
    # ------------------------------------------------------------------
    def _handle_opacity_key(self, event) -> bool:
        """Ctrl+Up and Ctrl+Down adjust opacity; returns True when handled."""
        if not self._opacity_supported:
            return False
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return False
        if event.key() == Qt.Key.Key_Up:
            self._nudge_opacity(OPACITY_STEP_PERCENT)
            return True
        if event.key() == Qt.Key.Key_Down:
            self._nudge_opacity(-OPACITY_STEP_PERCENT)
            return True
        return False

    def _handle_opacity_wheel(self, event) -> bool:
        """Ctrl+wheel adjusts opacity; returns True when handled."""
        if not self._opacity_supported:
            return False
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return False
        delta = event.angleDelta().y()
        if delta == 0:
            return False
        step = OPACITY_STEP_PERCENT if delta > 0 else -OPACITY_STEP_PERCENT
        self._nudge_opacity(step)
        return True
