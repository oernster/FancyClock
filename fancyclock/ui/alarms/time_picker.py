"""Clock-face time picker: a tappable dial plus editable spin fields.

The dial mirrors the Material pattern: an hours mode with an outer ring
(1 to 12) and an inner ring (13 to 23 and 00), and a minutes mode with
labels every five minutes. Picking an hour switches to minutes. The two
spin fields stay in sync and carry the keyboard path: typing or arrow
keys work without the mouse, and focusing a field selects its dial mode.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from fancyclock.domain.alarms import HOURS_PER_DAY, MINUTES_PER_HOUR

DIAL_SIZE_PX = 230
OUTER_RADIUS_PX = 96
INNER_RADIUS_PX = 62
KNOB_RADIUS_PX = 15
CENTER_DOT_PX = 4
LABEL_FONT_PX = 12
RING_SPLIT_PX = 80
HOURS_ON_A_RING = 12
MINUTE_LABEL_STEP = 5
DEGREES_PER_TURN = 360.0
DEGREES_AT_TWELVE = 90.0

DIAL_BG = QColor("#1d2230")
DIAL_FG = QColor("#e8ecf4")
DIAL_MUTED = QColor("#8b93a7")
DIAL_ACCENT = QColor("#F59E0B")

MODE_HOURS = 0
MODE_MINUTES = 1

SPIN_FIELD_WIDTH_PX = 64


class ClockDial(QWidget):
    """The painted, clickable clock face."""

    hour_picked = Signal(int)
    minute_picked = Signal(int)
    switched_to_minutes = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(DIAL_SIZE_PX, DIAL_SIZE_PX)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._mode = MODE_HOURS
        self._hour = 7
        self._minute = 0

    def set_mode(self, mode: int) -> None:
        self._mode = mode
        self.update()

    def set_time(self, hour: int, minute: int) -> None:
        self._hour = hour
        self._minute = minute
        self.update()

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------
    def _center(self) -> QPointF:
        return QPointF(self.width() / 2.0, self.height() / 2.0)

    def _position_for(self, fraction: float, radius: float) -> QPointF:
        angle = math.radians(DEGREES_AT_TWELVE - fraction * DEGREES_PER_TURN)
        center = self._center()
        return QPointF(
            center.x() + radius * math.cos(angle),
            center.y() - radius * math.sin(angle),
        )

    def _selected_position(self) -> QPointF:
        if self._mode == MODE_HOURS:
            on_outer = 1 <= self._hour <= HOURS_ON_A_RING
            radius = OUTER_RADIUS_PX if on_outer else INNER_RADIUS_PX
            fraction = (self._hour % HOURS_ON_A_RING) / HOURS_ON_A_RING
            return self._position_for(fraction, radius)
        return self._position_for(self._minute / MINUTES_PER_HOUR, OUTER_RADIUS_PX)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self._center()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(DIAL_BG)
        painter.drawEllipse(self.rect())

        knob = self._selected_position()
        painter.setPen(QPen(DIAL_ACCENT, 2))
        painter.drawLine(center, knob)
        painter.setBrush(DIAL_ACCENT)
        painter.drawEllipse(knob, KNOB_RADIUS_PX, KNOB_RADIUS_PX)
        painter.drawEllipse(center, CENTER_DOT_PX, CENTER_DOT_PX)

        font = QFont(self.font())
        font.setPixelSize(LABEL_FONT_PX)
        painter.setFont(font)
        if self._mode == MODE_HOURS:
            self._paint_hour_labels(painter)
        else:
            self._paint_minute_labels(painter)

    def _paint_label(
        self, painter: QPainter, text: str, at: QPointF, selected: bool
    ) -> None:
        painter.setPen(QColor("#101319") if selected else DIAL_FG)
        box = KNOB_RADIUS_PX
        painter.drawText(
            int(at.x() - box),
            int(at.y() - box),
            box * 2,
            box * 2,
            Qt.AlignmentFlag.AlignCenter,
            text,
        )

    def _paint_hour_labels(self, painter: QPainter) -> None:
        for value in range(HOURS_PER_DAY):
            on_outer = 1 <= value <= HOURS_ON_A_RING
            radius = OUTER_RADIUS_PX if on_outer else INNER_RADIUS_PX
            fraction = (value % HOURS_ON_A_RING) / HOURS_ON_A_RING
            at = self._position_for(fraction, radius)
            if not on_outer:
                painter.setPen(DIAL_MUTED)
            self._paint_label(painter, f"{value:02d}", at, value == self._hour)

    def _paint_minute_labels(self, painter: QPainter) -> None:
        for value in range(0, MINUTES_PER_HOUR, MINUTE_LABEL_STEP):
            at = self._position_for(value / MINUTES_PER_HOUR, OUTER_RADIUS_PX)
            self._paint_label(painter, f"{value:02d}", at, value == self._minute)

    # ------------------------------------------------------------------
    # Mouse picking
    # ------------------------------------------------------------------
    def _pick(self, pos: QPointF) -> None:
        center = self._center()
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        angle = math.degrees(math.atan2(-dy, dx))
        fraction = (DEGREES_AT_TWELVE - angle) % DEGREES_PER_TURN
        fraction /= DEGREES_PER_TURN
        distance = math.hypot(dx, dy)

        if self._mode == MODE_HOURS:
            index = round(fraction * HOURS_ON_A_RING) % HOURS_ON_A_RING
            if distance >= RING_SPLIT_PX:
                hour = HOURS_ON_A_RING if index == 0 else index
            else:
                hour = 0 if index == 0 else index + HOURS_ON_A_RING
            self._hour = hour
            self.hour_picked.emit(hour)
        else:
            minute = round(fraction * MINUTES_PER_HOUR) % MINUTES_PER_HOUR
            self._minute = minute
            self.minute_picked.emit(minute)
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._pick(event.position())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._pick(event.position())

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self._mode == MODE_HOURS:
            self.set_mode(MODE_MINUTES)
            self.switched_to_minutes.emit()


class _ModeSpin(QSpinBox):
    """A spin field that selects its dial mode when focused."""

    focused = Signal()

    def focusInEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().focusInEvent(event)
        self.focused.emit()


class TimePicker(QWidget):
    """Dial plus HH:MM spin fields, kept in sync both ways."""

    time_changed = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._dial = ClockDial(self)
        self._dial.switched_to_minutes.connect(self._focus_minutes)

        self._hour_spin = _ModeSpin(self)
        self._hour_spin.setRange(0, HOURS_PER_DAY - 1)
        self._minute_spin = _ModeSpin(self)
        self._minute_spin.setRange(0, MINUTES_PER_HOUR - 1)
        for spin in (self._hour_spin, self._minute_spin):
            spin.setWrapping(True)
            spin.setFixedWidth(SPIN_FIELD_WIDTH_PX)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)

        fields = QHBoxLayout()
        fields.addStretch()
        fields.addWidget(self._hour_spin)
        fields.addWidget(QLabel(":", self))
        fields.addWidget(self._minute_spin)
        fields.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(fields)
        layout.addWidget(self._dial, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._hour_spin.valueChanged.connect(self._spin_changed)
        self._minute_spin.valueChanged.connect(self._spin_changed)
        self._hour_spin.focused.connect(lambda: self._dial.set_mode(MODE_HOURS))
        self._minute_spin.focused.connect(lambda: self._dial.set_mode(MODE_MINUTES))
        self._dial.hour_picked.connect(self._dial_picked_hour)
        self._dial.minute_picked.connect(self._dial_picked_minute)

        self.set_time(7, 0)

    def hour(self) -> int:
        """Return the selected hour (0 to 23)."""
        return self._hour_spin.value()

    def minute(self) -> int:
        """Return the selected minute (0 to 59)."""
        return self._minute_spin.value()

    def set_time(self, hour: int, minute: int) -> None:
        """Set both fields and the dial."""
        for spin, value in ((self._hour_spin, hour), (self._minute_spin, minute)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
        self._dial.set_time(hour, minute)
        self.time_changed.emit(hour, minute)

    def _spin_changed(self, _value: int) -> None:
        self._dial.set_time(self.hour(), self.minute())
        self.time_changed.emit(self.hour(), self.minute())

    def _dial_picked_hour(self, hour: int) -> None:
        self._hour_spin.blockSignals(True)
        self._hour_spin.setValue(hour)
        self._hour_spin.blockSignals(False)
        self.time_changed.emit(self.hour(), self.minute())

    def _dial_picked_minute(self, minute: int) -> None:
        self._minute_spin.blockSignals(True)
        self._minute_spin.setValue(minute)
        self._minute_spin.blockSignals(False)
        self.time_changed.emit(self.hour(), self.minute())

    def _focus_minutes(self) -> None:
        self._minute_spin.setFocus(Qt.FocusReason.OtherFocusReason)
