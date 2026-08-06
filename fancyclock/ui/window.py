"""Main application window."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, QTimeZone
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from fancyclock.application.alarms import AlarmService
from fancyclock.application.localization import LocalizationService
from fancyclock.application.resources import ResourcePaths
from fancyclock.application.settings import SettingsService
from fancyclock.application.skins import SkinService
from fancyclock.application.time_service import TimeService
from fancyclock.application.timezones import TimezoneService
from fancyclock.ui.alarms.controller import AlarmsUiController
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
FALLBACK_WINDOW_TITLE = "Fancy Clock"

# Saying the saved alarms did not load whole. The delay lets the window
# finish drawing first, so the warning appears over a clock rather than
# over nothing.
ALARM_LOAD_FAILED_TITLE_KEY = "alarms_load_failed_title"
ALARM_LOAD_FAILED_TEXT_KEY = "alarms_load_failed_text"
COUNT_PLACEHOLDER = "{count}"
ALARM_WARNING_DELAY_MS = 400
NOTHING_LOST = 0


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
        alarm_service: AlarmService | None = None,
        autostart=None,
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

        self.time_zone = QTimeZone.systemTimeZone()

        self._opacity_supported = self._supports_window_opacity()

        self.alarm_service = alarm_service
        self._alarm_load_warned = False

        self.alarms_controller = None
        if alarm_service is not None:
            self.alarms_controller = AlarmsUiController(
                window=self,
                alarm_service=alarm_service,
                settings=settings,
                autostart=autostart,
                i18n=i18n_manager,
                timezone_service=timezone_service,
                resources=resources,
            )

        self._create_menu_bar()
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
        if self._opacity_supported:
            self.animation = QPropertyAnimation(self, b"windowOpacity")
            self.animation.setDuration(FADE_DURATION_MS)
            self.animation.setStartValue(FADE_START_OPACITY)
            self.animation.setEndValue(self.settings.window_opacity())
            self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        self._restore_locale_and_timezone()
        self._apply_startup_skin()
        self._apply_startup_opacity()

        if self.alarms_controller is not None:
            self.alarms_controller.start()

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
            self.animation.setEndValue(self.settings.window_opacity())
            self.animation.start()
        self._warn_once_about_unreadable_alarms()

    def _warn_once_about_unreadable_alarms(self) -> None:
        """Say once that the saved alarms file was not read whole.

        Interrupting on startup is the right weight for this: an alarm that
        was dropped will not ring, so the user would otherwise find out by
        oversleeping. It is said once per run, never on a clean load, then
        deferred so it appears over a drawn window rather than a blank one.
        """
        if self._alarm_load_warned or self.alarm_service is None:
            return
        self._alarm_load_warned = True
        lost = self.alarm_service.entries_lost_on_load
        if lost <= NOTHING_LOST:
            return
        QTimer.singleShot(
            ALARM_WARNING_DELAY_MS, lambda: self._show_alarm_load_warning(lost)
        )

    def _show_alarm_load_warning(self, lost: int) -> None:
        """Show the modal naming how many saved entries could not be read."""
        text = self.i18n_manager.get_translation(ALARM_LOAD_FAILED_TEXT_KEY)
        QMessageBox.warning(
            self,
            self.i18n_manager.get_translation(ALARM_LOAD_FAILED_TITLE_KEY),
            text.replace(COUNT_PLACEHOLDER, self.i18n_manager.format_number(lost)),
        )

    def keyPressEvent(self, event):  # noqa: N802 (Qt override)
        if self._handle_opacity_key(event):
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event):  # noqa: N802 (Qt override)
        if self._handle_opacity_wheel(event):
            return
        super().wheelEvent(event)

    def closeEvent(self, event):  # noqa: N802 (Qt override)
        if self.alarms_controller is not None:
            self.alarms_controller.handle_close(event)
            if not event.isAccepted():
                return
        super().closeEvent(event)
