import math

from PySide6.QtCore import QPoint, QRectF, Qt, QDateTime, QUrl
from PySide6.QtGui import QColor, QPainter, QFont, QPolygon
from PySide6.QtWidgets import QWidget
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink, QVideoFrame

from localization.i18n_manager import LocalizationManager
from effects.galaxy import create_galaxy


class AnalogClock(QWidget):
    def __init__(self, parent=None, i18n_manager: LocalizationManager = None):
        super().__init__(parent)

        self.i18n_manager = i18n_manager
        self.time = QDateTime.currentDateTime()

        # --- Galaxy/starfield state (original effect) ---
        self.stars = []
        self.galaxy_radius = 100  # will be updated in resizeEvent

        # --- Video background state ---
        self._media_player: QMediaPlayer | None = None
        self._video_sink: QVideoSink | None = None
        self._current_frame = None  # QImage or None
        self._current_skin: str | None = None

        self.setMinimumSize(200, 200)

    # ------------------------------------------------------------------ #
    # Layout / resize
    # ------------------------------------------------------------------ #
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Galaxy radius based on widget size
        self.galaxy_radius = min(self.width(), self.height()) / 2.0
        # Recreate stars with the new radius; signature: create_galaxy(count, radius)
        self.stars = create_galaxy(700, self.galaxy_radius)

    # ------------------------------------------------------------------ #
    # Animation hooks used by main.py
    # ------------------------------------------------------------------ #
    def tick(self, qdatetime: QDateTime):
        """
        Called once per second from ClockWindow.update_time().
        """
        self.time = qdatetime
        self.update()

    def animate(self):
        """
        Called at ~60 FPS from ClockWindow.update_animation() to animate background.
        """
        # Update starfield
        for star in self.stars:
            try:
                star.update()
            except Exception:
                pass

        # Request repaint
        self.update()

    # ------------------------------------------------------------------ #
    # Video skin API
    # ------------------------------------------------------------------ #
    def set_video_skin(self, file_path: str | None):
        """
        Enable a looping mp4 background behind the clock.
        Pass None or empty string to return to the default galaxy background.
        """
        if not file_path:
            # Disable any active skin
            if self._media_player is not None:
                try:
                    self._media_player.stop()
                except Exception:
                    pass
            self._current_skin = None
            self._current_frame = None
            self.update()
            return

        # Lazily create the multimedia pipeline
        if self._media_player is None:
            self._media_player = QMediaPlayer(self)
            self._video_sink = QVideoSink(self)
            self._media_player.setVideoSink(self._video_sink)
            self._video_sink.videoFrameChanged.connect(self._on_video_frame_changed)
            # For Qt versions without setLoops, we also listen to mediaStatusChanged
            self._media_player.mediaStatusChanged.connect(self._on_media_status_changed)

            # If this Qt has setLoops, loop forever
            if hasattr(self._media_player, "setLoops"):
                try:
                    # -1 means infinite loop in Qt 6
                    self._media_player.setLoops(-1)
                except Exception:
                    pass

        self._current_skin = file_path
        try:
            self._media_player.setSource(QUrl.fromLocalFile(file_path))
            self._media_player.play()
        except Exception:
            # If anything goes wrong, fall back to the default background
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
        """
        Fallback loop implementation for Qt builds that don't support setLoops.
        """
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
        """
        Draw the current video frame scaled to fill the widget,
        preserving aspect ratio and cropping as needed.
        """
        if self._current_frame is None:
            return

        widget_rect = self.rect()
        if not widget_rect.isValid():
            return

        # Use QRectF consistently for drawImage to avoid type mismatch
        target_rect = QRectF(widget_rect)

        # Scale while keeping aspect ratio, then crop to the widget rect
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
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # --- Background: video skin or galaxy ---
        if self._current_frame is not None:
            self._draw_video_background(painter)
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0))

            # Draw galaxy AFTER centering so stars align correctly
            painter.save()
            painter.translate(self.width() / 2, self.height() / 2)

            for star in self.stars:
                try:
                    x, y = star.pos()
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(star.color())
                    painter.drawEllipse(int(x), int(y), int(star.size), int(star.size))
                except Exception:
                    continue

            painter.restore()

        # --- Clock face & hands (same as before) ---
        side = min(self.width(), self.height())
        painter.translate(self.width() / 2.0, self.height() / 2.0)
        painter.scale(side / 200.0, side / 200.0)

        # Hour numbers (with localization where available)
        painter.setPen(QColor(255, 165, 0))
        font = QFont()
        font.setPointSize(12)
        painter.setFont(font)

        for i in range(1, 13):
            angle = math.radians(i * 30 - 90)
            x = 80 * math.cos(angle)
            y = 80 * math.sin(angle)

            if self.i18n_manager is not None:
                try:
                    label = self.i18n_manager.format_number(i)
                except Exception:
                    label = str(i)
            else:
                label = str(i)

            painter.drawText(QRectF(x - 10, y - 10, 20, 20), Qt.AlignCenter, label)

        # Clock hands
        t = self.time.time()

        # Hour hand
        painter.save()
        painter.setBrush(QColor(200, 200, 220))
        painter.setPen(Qt.NoPen)
        painter.rotate((t.hour() % 12 + t.minute() / 60.0) * 30.0)
        painter.drawConvexPolygon(QPolygon([QPoint(7, 8), QPoint(-7, 8), QPoint(0, -50)]))
        painter.restore()

        # Minute hand
        painter.save()
        painter.setBrush(QColor(180, 180, 200))
        painter.setPen(Qt.NoPen)
        painter.rotate((t.minute() + t.second() / 60.0) * 6.0)
        painter.drawConvexPolygon(QPolygon([QPoint(6, 10), QPoint(-6, 10), QPoint(0, -70)]))
        painter.restore()

        # Second hand
        painter.save()
        painter.setBrush(QColor(255, 100, 100))
        painter.setPen(Qt.NoPen)
        painter.rotate(t.second() * 6.0)
        painter.drawConvexPolygon(QPolygon([QPoint(2, 10), QPoint(-2, 10), QPoint(0, -90)]))
        painter.restore()
