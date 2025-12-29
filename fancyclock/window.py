"""Main application window."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimeZone, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QSizePolicy, QVBoxLayout, QWidget

from analog_clock import AnalogClock
from digital_clock import DigitalClock
from localization.i18n_manager import LocalizationManager
from ntp_client import NTPClient
from utils import resource_path

from fancyclock.window_animation import WindowAnimationMixin
from fancyclock.window_drag import WindowDragMixin
from fancyclock.window_locale import WindowLocaleMixin
from fancyclock.window_menu import WindowMenuMixin
from fancyclock.window_opacity import WindowOpacityMixin
from fancyclock.window_skin import WindowSkinMixin
from fancyclock.window_time import WindowTimeMixin


class ClockWindow(
    QMainWindow,
    WindowMenuMixin,
    WindowSkinMixin,
    WindowTimeMixin,
    WindowAnimationMixin,
    WindowLocaleMixin,
    WindowDragMixin,
    WindowOpacityMixin,
):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window)
        self.setWindowIcon(QIcon(resource_path("clock.ico")))

        self._set_scaled_initial_size(1.5)

        self.i18n_manager = LocalizationManager()
        title = self.i18n_manager.get_translation("app_name")
        if title == "app_name":
            title = "Fancy Clock"
        self.setWindowTitle(title)

        self._create_menu_bar()

        self.ntp_client = NTPClient()
        self.time_offset = 0
        self.time_zone = QTimeZone.systemTimeZone()
        try:
            self.synchronize_time()
        except Exception:
            pass

        self.old_pos = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.analog_clock = AnalogClock(self, i18n_manager=self.i18n_manager)
        self.layout.addWidget(self.analog_clock)
        self.layout.addSpacing(10)

        self.digital_clock = DigitalClock(self, i18n_manager=self.i18n_manager)
        self.digital_clock.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layout.addWidget(self.digital_clock)

        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self.update_time)
        self.tick_timer.start(1000)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(16)

        self.animation = None
        if self._supports_window_opacity():
            self.animation = QPropertyAnimation(self, b"windowOpacity")
            self.animation.setDuration(1000)
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        self._restore_locale_and_timezone()
        self._apply_startup_skin()

        self.setWindowIcon(QIcon(resource_path("clock.ico")))

    def bring_to_front(self) -> None:
        if not self.isVisible():
            self.show()

        if self.isMinimized():
            self.showNormal()

        self.raise_()
        self.activateWindow()

        win = self.windowHandle()
        if win is not None:
            try:
                win.requestActivate()
            except Exception:
                pass

        self.setWindowState(
            (self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
        )

    def _set_scaled_initial_size(self, scale: float = 1.5) -> None:
        base_w, base_h = 400, 440
        self.resize(int(base_w * scale), int(base_h * scale))

    def showEvent(self, event):  # noqa: N802 (Qt override)
        super().showEvent(event)
        if self.animation is not None:
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.start()
