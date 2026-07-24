"""Digital clock widget with a galaxy-filled bordered box."""

from __future__ import annotations

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from fancyclock.application.localization import LocalizationService
from fancyclock.ui.effects import create_galaxy

STAR_COUNT = 500
WIDGET_HEIGHT = 80
BOX_MARGIN = 8
BOX_CORNER_RADIUS = 10
TEXT_FONT_PT = 22
TIME_PAD_WIDTH = 2

BACKGROUND_COLOR = QColor(0, 0, 0)
BORDER_COLOR = QColor(255, 215, 0)
TEXT_COLOR = QColor(0, 150, 255)


class DigitalClock(QWidget):
    def __init__(self, parent=None, i18n_manager: LocalizationService | None = None):
        super().__init__(parent)

        self.i18n_manager = i18n_manager
        self.time = QDateTime.currentDateTime()

        self.setFixedHeight(WIDGET_HEIGHT)

        self.stars = []
        self.galaxy_radius = WIDGET_HEIGHT / 2.0

    # ------------------------------------------------------------------ #
    # Resize: recompute galaxy parameters
    # ------------------------------------------------------------------ #
    def resizeEvent(self, event):  # noqa: N802 (Qt override)
        super().resizeEvent(event)

        galaxy_rect = self.rect().adjusted(
            BOX_MARGIN, BOX_MARGIN, -BOX_MARGIN, -BOX_MARGIN
        )
        self.galaxy_radius = min(galaxy_rect.width(), galaxy_rect.height()) / 2
        self.stars = create_galaxy(STAR_COUNT, self.galaxy_radius)

    # ------------------------------------------------------------------ #
    # Animation hooks driven by ClockWindow
    # ------------------------------------------------------------------ #
    def tick(self, qdatetime: QDateTime):
        """Called once per second with the current (offset, zoned) time."""
        self.time = qdatetime
        self.update()

    def animate(self):
        """Called at ~60 FPS to animate the background."""
        for star in self.stars:
            star.update()
        self.update()

    # ------------------------------------------------------------------ #
    # Painting
    # ------------------------------------------------------------------ #
    def paintEvent(self, event):  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), BACKGROUND_COLOR)

        box_rect = self.rect().adjusted(
            BOX_MARGIN, BOX_MARGIN, -BOX_MARGIN, -BOX_MARGIN
        )

        painter.save()
        painter.setClipRect(box_rect)

        cx = box_rect.x() + box_rect.width() / 2
        cy = box_rect.y() + box_rect.height() / 2

        full_w = box_rect.width()
        full_h = box_rect.height()

        painter.translate(cx, cy)

        for star in self.stars:
            x, y = star.pos()

            sx = x * (full_w / (2 * self.galaxy_radius))
            sy = y * (full_h / (2 * self.galaxy_radius))

            painter.setPen(Qt.NoPen)
            painter.setBrush(star.color())
            painter.drawEllipse(int(sx), int(sy), int(star.size), int(star.size))

        painter.restore()

        painter.setPen(BORDER_COLOR)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(box_rect, BOX_CORNER_RADIUS, BOX_CORNER_RADIUS)

        dt = self.time

        if self.i18n_manager:
            date_text = self.i18n_manager.format_date_fancy(dt.date())

            hour = self.i18n_manager.format_number(
                f"{dt.time().hour():0{TIME_PAD_WIDTH}d}"
            )
            minute = self.i18n_manager.format_number(
                f"{dt.time().minute():0{TIME_PAD_WIDTH}d}"
            )
            second = self.i18n_manager.format_number(
                f"{dt.time().second():0{TIME_PAD_WIDTH}d}"
            )
        else:
            date_text = dt.toString("ddd d MMM")
            hour = dt.toString("hh")
            minute = dt.toString("mm")
            second = dt.toString("ss")

        full_text = f"{date_text}   {hour}:{minute}:{second}"

        font = QFont()
        font.setPointSize(TEXT_FONT_PT)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(TEXT_COLOR)

        painter.drawText(box_rect, Qt.AlignCenter, full_text)

        painter.end()
