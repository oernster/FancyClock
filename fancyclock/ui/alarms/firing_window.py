"""The persistent firing window shown while an alarm rings."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from fancyclock.domain.alarms import SNOOZE_PRESET_MINUTES, color_hex
from fancyclock.ui import theme
from fancyclock.ui.alarms.formatting import duration_text, time_text

WINDOW_MIN_WIDTH = 380
HEADER_PADDING_PX = 18
TIME_FONT_PX = 40
LABEL_FONT_PX = 18


def _header_style(hex_value: str) -> str:
    return (
        f"QWidget#FiringHeader {{ background-color: {hex_value};"
        f" border-radius: 8px; }}"
        f" QLabel {{ color: {theme.ON_ACCENT}; }}"
    )


class AlarmFiringWindow(QDialog):
    """Stays up until Dismiss or Snooze; closing the window dismisses."""

    snoozed = Signal(str, int)
    dismissed = Signal(str)

    def __init__(
        self,
        i18n,
        ringing,
        effective_minutes: int,
        snoozes_remaining: int | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._alarm_id = ringing.alarm.alarm_id
        self._resolved = False

        self.setWindowTitle(i18n.get_translation("alarm_ringing_title"))
        self.setMinimumWidth(WINDOW_MIN_WIDTH)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)

        header = QWidget(self)
        header.setObjectName("FiringHeader")
        header.setStyleSheet(_header_style(color_hex(ringing.alarm.color)))
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(
            HEADER_PADDING_PX,
            HEADER_PADDING_PX,
            HEADER_PADDING_PX,
            HEADER_PADDING_PX,
        )

        time_label = QLabel(
            time_text(i18n, ringing.alarm.hour, ringing.alarm.minute), header
        )
        time_label.setStyleSheet(f"font-size: {TIME_FONT_PX}px; font-weight: bold;")
        header_layout.addWidget(time_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        if ringing.alarm.label:
            name_label = QLabel(ringing.alarm.label, header)
            name_label.setStyleSheet(f"font-size: {LABEL_FONT_PX}px;")
            header_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(header)

        if ringing.is_late:
            layout.addWidget(
                QLabel(i18n.get_translation("alarm_late_note"), self),
                alignment=Qt.AlignmentFlag.AlignHCenter,
            )

        actions = QHBoxLayout()
        self._snooze_button = QToolButton(self)
        self._snooze_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup
        )
        self._snooze_button.clicked.connect(
            lambda: self._resolve_snooze(effective_minutes)
        )
        menu = QMenu(self)
        for minutes in SNOOZE_PRESET_MINUTES:
            action = menu.addAction(duration_text(i18n, minutes))
            action.triggered.connect(
                lambda _checked=False, m=minutes: self._resolve_snooze(m)
            )
        self._snooze_button.setMenu(menu)
        self._set_snooze_text(effective_minutes, snoozes_remaining)
        if snoozes_remaining == 0:
            self._snooze_button.setEnabled(False)
        actions.addWidget(self._snooze_button)

        dismiss = QPushButton(i18n.get_translation("dismiss"), self)
        dismiss.setDefault(True)
        dismiss.clicked.connect(self._resolve_dismiss)
        actions.addWidget(dismiss)
        layout.addLayout(actions)

    def _set_snooze_text(self, minutes: int, snoozes_remaining: int | None) -> None:
        text = (
            f"{self._i18n.get_translation('snooze')} "
            f"{duration_text(self._i18n, minutes)}"
        )
        if snoozes_remaining is not None:
            left = self._i18n.get_translation("snoozes_left")
            text = f"{text} ({left.format(left=snoozes_remaining)})"
        self._snooze_button.setText(text)

    def _resolve_snooze(self, minutes: int) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.snoozed.emit(self._alarm_id, minutes)
        self.close()

    def _resolve_dismiss(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.dismissed.emit(self._alarm_id)
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if not self._resolved:
            self._resolved = True
            self.dismissed.emit(self._alarm_id)
        super().closeEvent(event)
