"""Transient in-app toast for courtesy notices."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

TOAST_DURATION_MS = 5000
TOAST_MARGIN_PX = 24
TOAST_PADDING_PX = 14
ACCENT_BAR_PX = 4
TOAST_BG = "#1d2230"
TOAST_FG = "#f2f4f8"


def _toast_style(accent_hex: str) -> str:
    return (
        f"QWidget#Toast {{ background-color: {TOAST_BG};"
        f" border-left: {ACCENT_BAR_PX}px solid {accent_hex};"
        f" border-radius: 6px; }}"
        f" QLabel {{ color: {TOAST_FG}; font-size: 13px; }}"
    )


class Toast(QWidget):
    """A frameless notice that fades out after a few seconds."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            TOAST_PADDING_PX, TOAST_PADDING_PX, TOAST_PADDING_PX, TOAST_PADDING_PX
        )
        self._label = QLabel(self)
        layout.addWidget(self._label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(
        self,
        text: str,
        accent_hex: str,
        duration_ms: int = TOAST_DURATION_MS,
    ) -> None:
        """Show ``text`` with an accent bar for ``duration_ms``."""
        self._label.setText(text)
        self.setStyleSheet(_toast_style(accent_hex))
        self.adjustSize()
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(
                area.right() - self.width() - TOAST_MARGIN_PX,
                area.bottom() - self.height() - TOAST_MARGIN_PX,
            )
        self.show()
        self.raise_()
        self._timer.start(duration_ms)
