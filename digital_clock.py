from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtWidgets import QWidget

from localization.i18n_manager import LocalizationManager
from effects.galaxy import create_galaxy


class DigitalClock(QWidget):
    def __init__(self, parent=None, i18n_manager: LocalizationManager = None):
        super().__init__(parent)

        self.i18n_manager = i18n_manager
        self.time = QDateTime.currentDateTime()

        self.setFixedHeight(80)

        # Galaxy starfield
        self.stars = []
        self.galaxy_radius = 50
        self.galaxy_rect = None  # full interior of the yellow box

    # ----------------------------------------------------------------------
    # Resize → recompute galaxy parameters (rect + stars)
    # ----------------------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)

        margin = 8
        self.galaxy_rect = self.rect().adjusted(margin, margin, -margin, -margin)

        # galaxy_radius = the base radius that stars generate inside
        # (we will stretch them into the rectangle later)
        self.galaxy_radius = (
            min(self.galaxy_rect.width(), self.galaxy_rect.height()) / 2
        )

        self.stars = create_galaxy(500, self.galaxy_radius)

    # ----------------------------------------------------------------------
    # Legacy compatibility for main.py
    # ----------------------------------------------------------------------
    def show_time(self):
        self.time = QDateTime.currentDateTime()
        self.update()
        self.animate()

    # ----------------------------------------------------------------------
    # Paint the digital clock with full-box galaxy
    # ----------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        # Yellow bordered box
        margin = 8
        box_rect = self.rect().adjusted(margin, margin, -margin, -margin)

        # ------------------------------------------------------------------
        # Draw GALAXY inside the yellow box only
        # ------------------------------------------------------------------
        painter.save()
        painter.setClipRect(box_rect)

        # Center of the yellow box
        cx = box_rect.x() + box_rect.width() / 2
        cy = box_rect.y() + box_rect.height() / 2

        # Dimensions of box interior
        full_w = box_rect.width()
        full_h = box_rect.height()

        painter.translate(cx, cy)

        # Stretch galaxy into the rectangular box
        for star in self.stars:
            x, y = star.pos()

            # Scale star positions from circular radius → rectangular box
            sx = x * (full_w / (2 * self.galaxy_radius))
            sy = y * (full_h / (2 * self.galaxy_radius))

            painter.setPen(Qt.NoPen)
            painter.setBrush(star.color())
            painter.drawEllipse(int(sx), int(sy), int(star.size), int(star.size))

        painter.restore()  # remove clip & translate

        # ------------------------------------------------------------------
        # Yellow border outline
        # ------------------------------------------------------------------
        painter.setPen(QColor(255, 215, 0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(box_rect, 10, 10)

        # ------------------------------------------------------------------
        # Localized date + time (in one horizontal line)
        # ------------------------------------------------------------------
        dt = self.time

        if self.i18n_manager:
            date_text = self.i18n_manager.format_date_fancy(dt.date())

            # Always pad to 2 digits, then localize digits
            hour = self.i18n_manager.format_number(f"{dt.time().hour():02d}")
            minute = self.i18n_manager.format_number(f"{dt.time().minute():02d}")
            second = self.i18n_manager.format_number(f"{dt.time().second():02d}")
        else:
            date_text = dt.toString("ddd d MMM")
            hour = dt.toString("hh")
            minute = dt.toString("mm")
            second = dt.toString("ss")

        full_text = f"{date_text}   {hour}:{minute}:{second}"

        font = QFont()
        font.setPointSize(22)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(0, 150, 255))

        painter.drawText(box_rect, Qt.AlignCenter, full_text)

        painter.end()

    # ----------------------------------------------------------------------
    # High-frequency animation (called ~60 FPS)
    # ----------------------------------------------------------------------
    def animate(self):
        for s in self.stars:
            s.update()
        self.update()
