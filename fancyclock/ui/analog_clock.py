"""Analog clock widget with galaxy or video-skin background."""

from __future__ import annotations

import math

from PySide6.QtCore import QDateTime, QPoint, QRectF, Qt, QUrl
from PySide6.QtGui import QColor, QFont, QPainter, QPolygon
from PySide6.QtMultimedia import QMediaPlayer, QVideoFrame, QVideoSink
from PySide6.QtWidgets import QWidget

from fancyclock.application.localization import LocalizationService
from fancyclock.ui.effects import create_galaxy

STAR_COUNT = 700
MIN_WIDGET_SIZE = 200
CLOCK_SCALE_REFERENCE = 200.0
HOUR_NUMBER_RADIUS = 80
HOUR_NUMBER_FONT_PT = 12
HOUR_NUMBER_BOX = 20
HOURS_ON_FACE = 12
DEGREES_PER_HOUR = 30.0
DEGREES_PER_MINUTE = 6.0
DEGREES_PER_SECOND = 6.0
MINUTES_PER_HOUR = 60.0
SECONDS_PER_MINUTE = 60.0
INFINITE_LOOPS = -1

HOUR_NUMBER_COLOR = QColor(255, 165, 0)
HOUR_HAND_COLOR = QColor(200, 200, 220)
MINUTE_HAND_COLOR = QColor(180, 180, 200)
SECOND_HAND_COLOR = QColor(255, 100, 100)
BACKGROUND_COLOR = QColor(0, 0, 0)

HOUR_HAND_POLYGON = (QPoint(7, 8), QPoint(-7, 8), QPoint(0, -50))
MINUTE_HAND_POLYGON = (QPoint(6, 10), QPoint(-6, 10), QPoint(0, -70))
SECOND_HAND_POLYGON = (QPoint(2, 10), QPoint(-2, 10), QPoint(0, -90))


class AnalogClock(QWidget):
    def __init__(self, parent=None, i18n_manager: LocalizationService | None = None):
        super().__init__(parent)

        self.i18n_manager = i18n_manager
        self.time = QDateTime.currentDateTime()

        self.stars = []
        self.galaxy_radius = MIN_WIDGET_SIZE / 2.0

        self._media_player: QMediaPlayer | None = None
        self._video_sink: QVideoSink | None = None
        self._current_frame = None
        self._current_skin: str | None = None

        self.setMinimumSize(MIN_WIDGET_SIZE, MIN_WIDGET_SIZE)

    # ------------------------------------------------------------------ #
    # Layout / resize
    # ------------------------------------------------------------------ #
    def resizeEvent(self, event):  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self.galaxy_radius = min(self.width(), self.height()) / 2.0
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
    # Video skin API
    # ------------------------------------------------------------------ #
    def set_video_skin(self, file_path: str | None):
        """Enable a looping mp4 background; ``None`` restores the galaxy."""
        if not file_path:
            if self._media_player is not None:
                try:
                    self._media_player.stop()
                except Exception:
                    pass
            self._current_skin = None
            self._current_frame = None
            self.update()
            return

        if self._media_player is None:
            self._media_player = QMediaPlayer(self)
            self._video_sink = QVideoSink(self)
            self._media_player.setVideoSink(self._video_sink)
            self._video_sink.videoFrameChanged.connect(self._on_video_frame_changed)
            self._media_player.mediaStatusChanged.connect(self._on_media_status_changed)
            if hasattr(self._media_player, "setLoops"):
                try:
                    self._media_player.setLoops(INFINITE_LOOPS)
                except Exception:
                    pass

        self._current_skin = file_path
        try:
            self._media_player.setSource(QUrl.fromLocalFile(file_path))
            self._media_player.play()
        except Exception:
            self._current_skin = None
            self._current_frame = None
            self.update()

    def _on_video_frame_changed(self, frame: QVideoFrame):
        """Store the most recent frame so paintEvent can draw it."""
        try:
            image = frame.toImage()
        except Exception:
            image = None

        if image is None or image.isNull():
            return

        self._current_frame = image
        self.update()

    def _on_media_status_changed(self, status):
        """Fallback loop for Qt builds without ``setLoops`` support."""
        try:
            if (
                self._media_player is not None
                and getattr(QMediaPlayer, "EndOfMedia", None) is not None
                and status == QMediaPlayer.EndOfMedia
            ):
                self._media_player.setPosition(0)
                self._media_player.play()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Background drawing helpers
    # ------------------------------------------------------------------ #
    def _draw_video_background(self, painter: QPainter):
        """Draw the current video frame scaled to fill the widget."""
        if self._current_frame is None:
            return

        widget_rect = self.rect()
        if not widget_rect.isValid():
            return

        target_rect = QRectF(widget_rect)

        scaled = self._current_frame.scaled(
            widget_rect.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        if scaled.isNull():
            return

        x = max(0, (scaled.width() - widget_rect.width()) // 2)
        y = max(0, (scaled.height() - widget_rect.height()) // 2)

        source_rect = QRectF(
            float(x),
            float(y),
            float(widget_rect.width()),
            float(widget_rect.height()),
        )

        painter.drawImage(target_rect, scaled, source_rect)

    # ------------------------------------------------------------------ #
    # Painting
    # ------------------------------------------------------------------ #
    def paintEvent(self, event):  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._current_frame is not None:
            self._draw_video_background(painter)
        else:
            painter.fillRect(self.rect(), BACKGROUND_COLOR)

            painter.save()
            painter.translate(self.width() / 2, self.height() / 2)

            for star in self.stars:
                x, y = star.pos()
                painter.setPen(Qt.NoPen)
                painter.setBrush(star.color())
                painter.drawEllipse(int(x), int(y), int(star.size), int(star.size))

            painter.restore()

        side = min(self.width(), self.height())
        painter.translate(self.width() / 2.0, self.height() / 2.0)
        painter.scale(side / CLOCK_SCALE_REFERENCE, side / CLOCK_SCALE_REFERENCE)

        painter.setPen(HOUR_NUMBER_COLOR)
        font = QFont()
        font.setPointSize(HOUR_NUMBER_FONT_PT)
        painter.setFont(font)

        half_box = HOUR_NUMBER_BOX / 2
        for i in range(1, HOURS_ON_FACE + 1):
            angle = math.radians(i * DEGREES_PER_HOUR - 90)
            x = HOUR_NUMBER_RADIUS * math.cos(angle)
            y = HOUR_NUMBER_RADIUS * math.sin(angle)

            if self.i18n_manager is not None:
                label = self.i18n_manager.format_number(i)
            else:
                label = str(i)

            painter.drawText(
                QRectF(x - half_box, y - half_box, HOUR_NUMBER_BOX, HOUR_NUMBER_BOX),
                Qt.AlignCenter,
                label,
            )

        t = self.time.time()

        painter.save()
        painter.setBrush(HOUR_HAND_COLOR)
        painter.setPen(Qt.NoPen)
        painter.rotate(
            (t.hour() % HOURS_ON_FACE + t.minute() / MINUTES_PER_HOUR)
            * DEGREES_PER_HOUR
        )
        painter.drawConvexPolygon(QPolygon(list(HOUR_HAND_POLYGON)))
        painter.restore()

        painter.save()
        painter.setBrush(MINUTE_HAND_COLOR)
        painter.setPen(Qt.NoPen)
        painter.rotate(
            (t.minute() + t.second() / SECONDS_PER_MINUTE) * DEGREES_PER_MINUTE
        )
        painter.drawConvexPolygon(QPolygon(list(MINUTE_HAND_POLYGON)))
        painter.restore()

        painter.save()
        painter.setBrush(SECOND_HAND_COLOR)
        painter.setPen(Qt.NoPen)
        painter.rotate(t.second() * DEGREES_PER_SECOND)
        painter.drawConvexPolygon(QPolygon(list(SECOND_HAND_POLYGON)))
        painter.restore()
