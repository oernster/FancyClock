import math
import math
import random
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPolygon, QBrush, QLinearGradient, QFont
from PySide6.QtCore import QPoint, QTime, Qt, QRectF, QDateTime

class Star:
    def __init__(self, angle, distance, radius, velocity):
        self.angle = angle
        self.distance = distance
        self.radius = radius
        self.velocity = velocity
        self.x = 0
        self.y = 0

from localization.i18n_manager import I18nManager

class AnalogClock(QWidget):
    def __init__(self, parent=None, i18n_manager: I18nManager = None):
        super().__init__(parent)
        self.i18n_manager = i18n_manager
        self.setMinimumSize(200, 200)
        self.time = QDateTime.currentDateTime()
        self.stars = [self._create_star() for _ in range(200)]

    def _create_star(self):
        return Star(
            angle=random.uniform(0, 2 * math.pi),
            distance=random.uniform(0, 100),
            radius=random.uniform(0.5, 2),
            velocity=random.uniform(0.001, 0.005)
        )

    def update_stars(self):
        for star in self.stars:
            star.angle += star.velocity
            star.x = star.distance * math.cos(star.angle)
            star.y = star.distance * math.sin(star.angle)
            if star.angle > 2 * math.pi:
                star.angle = 0

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        time = self.time.time()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.setBrush(QColor(0, 0, 0))
        painter.drawRect(self.rect())

        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)
        
        # Stars
        painter.setPen(Qt.NoPen)
        for star in self.stars:
            alpha = random.randint(100, 255)
            painter.setBrush(QColor(255, 255, 255, alpha))
            painter.drawEllipse(QPoint(int(star.x), int(star.y)), star.radius, star.radius)

        # Hour markers
        painter.setPen(QColor(255, 165, 0))  # Light Orange
        font = QFont()
        font.setPointSize(12)
        painter.setFont(font)
        for i in range(1, 13):
            angle = math.radians(i * 30 - 90)
            x = 80 * math.cos(angle)
            y = 80 * math.sin(angle)
            number_str = self.i18n_manager.format_number(i) if self.i18n_manager else str(i)
            painter.drawText(QRectF(x - 10, y - 10, 20, 20), Qt.AlignCenter, number_str)

        # Date and Day
        date_rect = QRectF(15, -10, 50, 20)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QColor(255, 255, 0))
        painter.drawRoundedRect(date_rect, 5, 5)

        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor(144, 238, 144))  # Light Green
        if self.i18n_manager:
            weekday_keys = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            day_of_week = self.time.date().dayOfWeek() - 1  # Adjust for 0-based index
            day_key = f"calendar.days.{weekday_keys[day_of_week]}"
            day_str = self.i18n_manager.get_translation(day_key)
            date_str = self.i18n_manager.format_number(self.time.date().day())
            date_text = f"{day_str} {date_str}"
        else:
            date_text = self.time.toString("ddd d")
        painter.drawText(date_rect, Qt.AlignCenter, date_text)


        # Hands
        hour_hand = QPolygon([QPoint(0, 0), QPoint(5, -40), QPoint(0, -50), QPoint(-5, -40)])
        minute_hand = QPolygon([QPoint(0, 0), QPoint(4, -60), QPoint(0, -70), QPoint(-4, -60)])
        second_hand = QPolygon([QPoint(0, 20), QPoint(2, -80), QPoint(0, -90), QPoint(-2, -80)])

        hour_color = QColor(220, 220, 240)
        minute_color = QColor(200, 200, 255)
        second_color = QColor(255, 100, 100)

        painter.save()
        painter.setBrush(QBrush(hour_color))
        painter.setPen(Qt.NoPen)
        painter.rotate(30.0 * (time.hour() + time.minute() / 60.0))
        painter.drawConvexPolygon(hour_hand)
        painter.restore()

        painter.save()
        painter.setBrush(QBrush(minute_color))
        painter.setPen(Qt.NoPen)
        painter.rotate(6.0 * (time.minute() + time.second() / 60.0))
        painter.drawConvexPolygon(minute_hand)
        painter.restore()

        painter.save()
        painter.setBrush(QBrush(second_color))
        painter.setPen(Qt.NoPen)
        painter.rotate(6.0 * time.second())
        painter.drawConvexPolygon(second_hand)
        painter.restore()

        # Center circle
        painter.setBrush(QBrush(QColor(50, 50, 70)))
        painter.drawEllipse(-5, -5, 10, 10)