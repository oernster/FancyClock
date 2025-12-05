import random
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCore import QDateTime, Qt, QRectF, QPoint

import math

class Star:
    def __init__(self, angle, distance, radius, velocity):
        self.angle = angle
        self.distance = distance
        self.radius = radius
        self.velocity = velocity
        self.x = 0
        self.y = 0

class DigitalClock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.time = QDateTime.currentDateTime()
        self.stars = []

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.stars = [self._create_star() for _ in range(400)]

    def _create_star(self):
        # The distance should be calculated based on the diagonal to cover the whole area
        max_dist = math.sqrt(self.width()**2 + self.height()**2) / 2
        return Star(
            angle=random.uniform(0, 2 * math.pi),
            distance=random.uniform(0, max_dist),
            radius=random.uniform(0.5, 1.5),
            velocity=random.uniform(0.001, 0.005)
        )

    def update_stars(self):
        center_x = self.width() / 2
        center_y = self.height() / 2
        for star in self.stars:
            star.angle += star.velocity
            star.x = center_x + star.distance * math.cos(star.angle)
            star.y = center_y + star.distance * math.sin(star.angle)
            if star.angle > 2 * math.pi:
                star.angle = 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.setBrush(QColor(0, 0, 0))
        painter.drawRect(self.rect())

        # Stars
        painter.setPen(Qt.NoPen)
        for star in self.stars:
            alpha = random.randint(100, 255)
            painter.setBrush(QColor(255, 255, 255, alpha))
            painter.drawEllipse(QPoint(int(star.x), int(star.y)), star.radius, star.radius)

        # Border
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QColor(255, 255, 0))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 5, 5)

        # Time text
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(173, 216, 230))  # Light Blue
        
        time_text = self.time.time().toString("hh:mm:ss")
        painter.drawText(self.rect(), Qt.AlignCenter, time_text)

    def show_time(self):
        self.update()