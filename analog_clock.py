import math
from PySide6.QtCore import QPoint, QRectF, Qt, QDateTime
from PySide6.QtGui import QColor, QPainter, QFont, QPolygon
from PySide6.QtWidgets import QWidget

from localization.i18n_manager import LocalizationManager
from effects.galaxy import create_galaxy


class AnalogClock(QWidget):
    def __init__(self, parent=None, i18n_manager: LocalizationManager = None):
        super().__init__(parent)
        self.i18n_manager = i18n_manager
        self.time = QDateTime.currentDateTime()
        self.stars = []
        self.galaxy_radius = 100  # updated in resizeEvent

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.galaxy_radius = min(self.width(), self.height()) / 2
        self.stars = create_galaxy(700, self.galaxy_radius)

    def animate(self):
        """Called ~60 times per second from main.py"""
        for s in self.stars:
            s.update()
        self.update()   # repaint immediately

    def update_stars(self):
        for s in self.stars:
            s.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        # Center & scale
        side = min(self.width(), self.height())
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        # --- Galaxy stars ---
        painter.save()
        for star in self.stars:
            x, y = star.pos()
            painter.setPen(Qt.NoPen)
            painter.setBrush(star.color())
            painter.drawEllipse(int(x), int(y), int(star.size), int(star.size))
        painter.restore()

        # --- Hour numbers ---
        painter.setPen(QColor(255, 165, 0))
        font = QFont()
        font.setPointSize(12)
        painter.setFont(font)

        for i in range(1, 13):
            angle = math.radians(i * 30 - 90)
            x = 80 * math.cos(angle)
            y = 80 * math.sin(angle)
            label = (
                self.i18n_manager.format_number(i)
                if self.i18n_manager else
                str(i)
            )
            painter.drawText(QRectF(x - 10, y - 10, 20, 20), Qt.AlignCenter, label)

        # --- Clock hands ---
        time = self.time.time()

        # Hour hand
        painter.save()
        painter.setBrush(QColor(200, 200, 220))
        painter.setPen(Qt.NoPen)
        painter.rotate((time.hour() % 12 + time.minute() / 60) * 30)
        painter.drawConvexPolygon(QPolygon([QPoint(7, 8), QPoint(-7, 8), QPoint(0, -50)]))
        painter.restore()

        # Minute hand
        painter.save()
        painter.setBrush(QColor(180, 180, 200))
        painter.setPen(Qt.NoPen)
        painter.rotate((time.minute() + time.second() / 60) * 6)
        painter.drawConvexPolygon(QPolygon([QPoint(6, 10), QPoint(-6, 10), QPoint(0, -70)]))
        painter.restore()

        # Second hand
        painter.save()
        painter.setBrush(QColor(255, 100, 100))
        painter.setPen(Qt.NoPen)
        painter.rotate(time.second() * 6)
        painter.drawConvexPolygon(QPolygon([QPoint(2, 10), QPoint(-2, 10), QPoint(0, -90)]))
        painter.restore()

        painter.end()
