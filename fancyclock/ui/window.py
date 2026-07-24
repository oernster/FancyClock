"""Main application window."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, QTimeZone
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QSizePolicy, QVBoxLayout, QWidget

from fancyclock.application.localization import LocalizationService
from fancyclock.application.resources import ResourcePaths
from fancyclock.application.settings import SettingsService
from fancyclock.application.skins import SkinService
from fancyclock.application.time_service import TimeService
from fancyclock.application.timezones import TimezoneService
from fancyclock.ui.analog_clock import AnalogClock
from fancyclock.ui.digital_clock import DigitalClock
from fancyclock.ui.window_animation import WindowAnimationMixin
from fancyclock.ui.window_drag import WindowDragMixin
from fancyclock.ui.window_locale import WindowLocaleMixin
from fancyclock.ui.window_menu import WindowMenuMixin
from fancyclock.ui.window_opacity import WindowOpacityMixin
from fancyclock.ui.window_skin import WindowSkinMixin
from fancyclock.ui.window_time import WindowTimeMixin

BASE_WIDTH = 400
BASE_HEIGHT = 440
INITIAL_SCALE = 1.5
TICK_INTERVAL_MS = 1000
ANIMATION_INTERVAL_MS = 16
FADE_DURATION_MS = 1000
CLOCK_SPACING_PX = 10
FADE_START_OPACITY = 0.0
FADE_END_OPACITY = 1.0
FALLBACK_WINDOW_TITLE = "Fancy Clock"


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
    def __init__(
        self,
        i18n_manager: LocalizationService,
        time_service: TimeService,
        settings: SettingsService,
        skin_service: SkinService,
        timezone_service: TimezoneService,
        resources: ResourcePaths,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.i18n_manager = i18n_manager
        self.time_service = time_service
        self.settings = settings
        self.skin_service = skin_service
        self.timezone_service = timezone_service
        self.resources = resources

        self.setWindowFlags(Qt.Window)
        self.setWindowIcon(QIcon(resources.app_icon))

        self._set_scaled_initial_size(INITIAL_SCALE)

        title = self.i18n_manager.get_translation("app_name")
        if title == "app_name":
            title = FALLBACK_WINDOW_TITLE
        self.setWindowTitle(title)

        self._create_menu_bar()

        self.time_zone = QTimeZone.systemTimeZone()
        try:
            self.synchronize_time()
        except Exception:
            pass

        self.old_pos = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)

        self.analog_clock = AnalogClock(self, i18n_manager=self.i18n_manager)
        self.central_layout.addWidget(self.analog_clock)
        self.central_layout.addSpacing(CLOCK_SPACING_PX)

        self.digital_clock = DigitalClock(self, i18n_manager=self.i18n_manager)
        self.digital_clock.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.central_layout.addWidget(self.digital_clock)

        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self.update_time)
        self.tick_timer.start(TICK_INTERVAL_MS)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(ANIMATION_INTERVAL_MS)

        self.animation = None
        if self._supports_window_opacity():
            self.animation = QPropertyAnimation(self, b"windowOpacity")
            self.animation.setDuration(FADE_DURATION_MS)
            self.animation.setStartValue(FADE_START_OPACITY)
            self.animation.setEndValue(FADE_END_OPACITY)
            self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        self._restore_locale_and_timezone()
        self._apply_startup_skin()

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

    def _set_scaled_initial_size(self, scale: float) -> None:
        self.resize(int(BASE_WIDTH * scale), int(BASE_HEIGHT * scale))

    def showEvent(self, event):  # noqa: N802 (Qt override)
        super().showEvent(event)
        if self.animation is not None:
            self.animation.setStartValue(FADE_START_OPACITY)
            self.animation.setEndValue(FADE_END_OPACITY)
            self.animation.start()
