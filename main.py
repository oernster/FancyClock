import sys
import os
import ctypes
from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QMessageBox,
)
from PySide6.QtGui import (
    QAction,
    QIcon,
)
from PySide6.QtCore import (
    QTimer,
    QDateTime,
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    QTimeZone,
    QLoggingCategory,
    QSystemSemaphore,
    QSharedMemory,
    QObject,
    Signal,
    QSettings,
    QCoreApplication,
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket


from analog_clock import AnalogClock
from digital_clock import DigitalClock
from ntp_client import NTPClient
from localization.i18n_manager import LocalizationManager
from utils import resource_path
from dialogs import show_timezone_dialog, AboutDialog, LicenseDialog
from single_instance import SingleInstanceGuard


class ClockWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window)
        self.setWindowIcon(QIcon(resource_path("clock.ico")))

        # Scale initial window size by 1.5x (keeps previous behaviour)
        self._set_scaled_initial_size(1.5)

        # i18n manager
        self.i18n_manager = LocalizationManager()
        title = self.i18n_manager.get_translation("app_name")
        if title == "app_name":  # translation missing
            title = "Fancy Clock"
        self.setWindowTitle(title)

        # menu
        self._create_menu_bar()

        # time sync
        self.ntp_client = NTPClient()
        self.time_offset = 0
        self.time_zone = QTimeZone.systemTimeZone()
        # best-effort sync (non-blocking)
        try:
            self.synchronize_time()
        except Exception:
            # ignore network/NTP issues at startup
            pass

        # dragging
        self.old_pos = None

        # central widget & layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # clocks
        self.analog_clock = AnalogClock(self, i18n_manager=self.i18n_manager)
        self.layout.addWidget(self.analog_clock)
        self.layout.addSpacing(10)

        self.digital_clock = DigitalClock(self, i18n_manager=self.i18n_manager)
        self.digital_clock.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layout.addWidget(self.digital_clock)

        # timers
        # 1) Tick timer (once per second)
        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self.update_time)
        self.tick_timer.start(1000)

        # 2) Animation timer (~60 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(16)

        # fade-in animation on show (only if platform supports opacity)
        self.animation = None
        if self._supports_window_opacity():
            self.animation = QPropertyAnimation(self, b"windowOpacity")
            self.animation.setDuration(1000)
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Restore saved locale/timezone and apply startup skin
        self._restore_locale_and_timezone()
        self._apply_startup_skin()

        icon_path = resource_path("clock.ico")
        self.setWindowIcon(QIcon(icon_path))

    def bring_to_front(self):
        """
        Try to make this window visible, un-minimized, and focused on
        both Windows and Linux (X11/Wayland).
        """
        # Ensure it’s at least shown
        if not self.isVisible():
            self.show()

        # If minimized, restore it
        if self.isMinimized():
            self.showNormal()

        # Raise and activate
        self.raise_()
        self.activateWindow()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)

    def _supports_window_opacity(self) -> bool:
        """
        Check whether the platform supports window opacity.
        """
        try:
            self.setWindowOpacity(0.99)
            return True
        except Exception:
            return False

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # dummy menu to keep corner widget layout behavior consistent
        menu_bar.addMenu("").addAction(QAction("", self))
        menu_bar.setCornerWidget(spacer)

        # Timezone action
        self.timezone_action = QAction(self.i18n_manager.get_translation("timezone"), self)
        self.timezone_action.triggered.connect(lambda: show_timezone_dialog(self))
        menu_bar.addAction(self.timezone_action)

        # Skins menu with video backgrounds for the analog clock
        skins_label = self.i18n_manager.get_translation("skins")
        if skins_label == "skins":  # translation missing
            skins_label = "Skins"
        self.skins_menu = menu_bar.addMenu(skins_label)
        self._populate_skins_menu()

        # Help menu
        self.help_menu = menu_bar.addMenu(self.i18n_manager.get_translation("help"))
        self.about_action = QAction(self.i18n_manager.get_translation("about"), self)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.help_menu.addAction(self.about_action)

        self.license_action = QAction(self.i18n_manager.get_translation("license"), self)
        self.license_action.triggered.connect(self.show_license_dialog)
        self.help_menu.addAction(self.license_action)

    def show_about_dialog(self):
        if not hasattr(self, "about_dialog") or self.about_dialog is None:
            self.about_dialog = AboutDialog(self.i18n_manager, self)
        self.about_dialog.refresh_text()
        self.about_dialog.show()
        self.about_dialog.raise_()
        self.about_dialog.activateWindow()

    def show_license_dialog(self):
        if not hasattr(self, "license_dialog") or self.license_dialog is None:
            self.license_dialog = LicenseDialog(self.i18n_manager, self)
        self.license_dialog.refresh_text()
        self.license_dialog.show()
        self.license_dialog.raise_()
        self.license_dialog.activateWindow()

    def _settings(self) -> QSettings:
        """Convenience accessor for application settings."""
        return QSettings()

    def _find_skin_by_name(self, name: str) -> str | None:
        """Search media/ for an mp4 whose stem matches the given name (case-insensitive)."""
        media_dir = resource_path("media")
        if not os.path.isdir(media_dir):
            return None

        name = name.lower()
        for filename in os.listdir(media_dir):
            if not filename.lower().endswith(".mp4"):
                continue
            stem, _ = os.path.splitext(filename)
            if stem.lower() == name:
                return os.path.join(media_dir, filename)
        return None

    def _apply_startup_skin(self) -> None:
        """Apply saved skin if present, otherwise default to 'Mesmerize' if available."""
        settings = self._settings()
        saved_skin = settings.value("skin_path", None, type=str)

        if saved_skin and os.path.isfile(saved_skin):
            self.analog_clock.set_video_skin(saved_skin)
            return

        mesmerize = self._find_skin_by_name("mesmerize")
        if mesmerize:
            self.analog_clock.set_video_skin(mesmerize)
            settings.setValue("skin_path", mesmerize)

    def _set_skin_and_persist(self, path: str | None) -> None:
        """Set the current skin and persist it in settings."""
        self.analog_clock.set_video_skin(path)
        settings = self._settings()
        if path:
            settings.setValue("skin_path", path)
        else:
            settings.remove("skin_path")

    def _populate_skins_menu(self):
        """(Re)build the Skins menu from media/*.mp4 files."""
        if not hasattr(self, "skins_menu"):
            return

        self.skins_menu.clear()

        # First entry: go back to the built-in galaxy background
        default_label = self.i18n_manager.get_translation("skin_default")
        if default_label == "skin_default":  # translation missing
            default_label = "Default (Galaxy)"
        default_action = QAction(default_label, self)
        default_action.triggered.connect(lambda: self._set_skin_and_persist(None))
        self.skins_menu.addAction(default_action)

        media_dir = resource_path("media")
        if not os.path.isdir(media_dir):
            return

        # One menu entry per *.mp4 file in the media folder
        for filename in sorted(os.listdir(media_dir)):
            if not filename.lower().endswith(".mp4"):
                continue
            path = os.path.join(media_dir, filename)
            nice_name = os.path.splitext(filename)[0].replace("_", " ").title()
            action = QAction(nice_name, self)
            action.triggered.connect(
                lambda checked=False, p=path: self._set_skin_and_persist(p)
            )
            self.skins_menu.addAction(action)

    def _restore_locale_and_timezone(self) -> None:
        """Restore saved locale and timezone from settings, if available."""
        settings = self._settings()

        saved_tz = settings.value("timezone_id", None, type=str)
        saved_locale = settings.value("locale", None, type=str)

        if saved_tz:
            try:
                self._change_timezone(saved_tz)
            except Exception:
                pass

        if saved_locale:
            try:
                self.i18n_manager.set_locale(saved_locale)
                self.retranslate_ui()
                self.update_time()
            except Exception:
                pass

    # Window sizing & show
    # -----------------------
    def _set_scaled_initial_size(self, scale: float = 1.5):
        base_w, base_h = 400, 440
        self.resize(int(base_w * scale), int(base_h * scale))

    def showEvent(self, event):
        super().showEvent(event)
        if self.animation is not None:
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.start()

    # -----------------------
    # Time / NTP helpers
    # -----------------------
    def synchronize_time(self):
        """
        Query NTP and compute an offset so we can use QDateTime + offset.
        If NTP fails, we keep offset = 0.
        """
        ntp_time = self.ntp_client.get_time()
        if isinstance(ntp_time, datetime):
            local_utc_now = datetime.now(timezone.utc)
            # offset in seconds
            self.time_offset = (ntp_time - local_utc_now).total_seconds()
        else:
            self.time_offset = 0

    def _current_time(self) -> QDateTime:
        """
        Compute the current time with NTP offset and selected timezone.
        """
        qdt = QDateTime.currentDateTimeUtc().addSecs(int(self.time_offset))
        return qdt.toTimeZone(self.time_zone)

    # -----------------------
    # Clock update helpers
    # -----------------------
    def _tick_clock(self, clock_widget, current_qdatetime: QDateTime):
        """
        Update a clock widget's current time in a clean, intention-revealing way.

        Preferred interface: clock_widget.tick(QDateTime)
        Fallbacks tried in order:
          - clock_widget.tick(QDateTime)
          - clock_widget.show_time()  (legacy)
          - clock_widget.time = QDateTime; clock_widget.update()
        """
        # 1) Preferred: tick(qdatetime)
        if hasattr(clock_widget, "tick") and callable(getattr(clock_widget, "tick")):
            try:
                clock_widget.tick(current_qdatetime)
                return
            except Exception:
                pass

        # 2) Legacy: show_time() which may read its own stored time
        if hasattr(clock_widget, "show_time") and callable(getattr(clock_widget, "show_time")):
            try:
                # If show_time expects the widget to have .time set, set it.
                if hasattr(clock_widget, "time"):
                    clock_widget.time = current_qdatetime
                clock_widget.show_time()
                return
            except Exception:
                pass

        # 3) Fallback: set attribute and request an update
        try:
            clock_widget.time = current_qdatetime
            clock_widget.update()
        except Exception:
            # last resort: call repaint
            try:
                clock_widget.repaint()
            except Exception:
                pass

    def update_time(self):
        """
        Slot called by the tick timer once per second.
        """
        current_qdatetime = self._current_time()

        # Update both clocks via the helper, so they can evolve independently
        self._tick_clock(self.analog_clock, current_qdatetime)
        self._tick_clock(self.digital_clock, current_qdatetime)

    # -----------------------
    # Animation helpers
    # -----------------------
    def _animate_clock(self, clock_widget):
        """
        Advance the clock's animation/state for the high-frequency animation loop.

        Preferred interface: clock_widget.animate()
        Fallbacks (in order):
          - animate()
          - update_galaxy()
          - update_stars()
          - update()
        """
        # Preferred API
        if hasattr(clock_widget, "animate") and callable(getattr(clock_widget, "animate")):
            try:
                clock_widget.animate()
                return
            except Exception:
                pass

        # Backwards-compatible APIs
        for method_name in ("update_galaxy", "update_stars", "update"):
            if hasattr(clock_widget, method_name) and callable(getattr(clock_widget, method_name)):
                try:
                    getattr(clock_widget, method_name)()
                    return
                except Exception:
                    continue

    def update_animation(self):
        """
        Slot called by the animation timer roughly 60 times per second.
        """
        self._animate_clock(self.analog_clock)
        self._animate_clock(self.digital_clock)

    # -----------------------
    # Localization helpers
    # -----------------------
    def _get_locale_for_timezone(self, tz_id):
        """
        Get the most appropriate locale for a given timezone.
        Falls back to en_US if nothing found.
        """
        try:
            return self.i18n_manager.locale_detector.get_locale_from_timezone(tz_id) or "en_US"
        except Exception:
            return "en_US"

    def _change_timezone(self, tz):
        """Update timezone, locale, persist both, and retranslate the UI."""
        try:
            self.time_zone = QTimeZone(tz.encode("utf-8"))
        except Exception:
            # if invalid tz id, ignore
            return

        # Persist timezone selection
        try:
            settings = self._settings()
            settings.setValue("timezone_id", tz)
        except Exception:
            pass

        # Derive and apply a suitable locale for this timezone
        locale = self._get_locale_for_timezone(tz)
        try:
            if locale:
                self.i18n_manager.set_locale(locale)
                # Persist the current locale for next launch
                settings = self._settings()
                settings.setValue("locale", self.i18n_manager.current_locale)
        except Exception:
            pass

        # Refresh UI strings and force an immediate tick so clocks show correct locale
        try:
            self.retranslate_ui()
            self.update_time()
        except Exception:
            pass

        # Refresh about dialog if visible
        try:
            if hasattr(self, "about_dialog") and self.about_dialog.isVisible():
                self.about_dialog.refresh_text()
        except Exception:
            pass

    def retranslate_ui(self):
        """
        Update UI text strings to the current locale.
        """
        try:
            self.setWindowTitle(self.i18n_manager.get_translation("app_name"))
        except Exception:
            pass

        try:
            self.timezone_action.setText(self.i18n_manager.get_translation("timezone"))
        except Exception:
            pass

        try:
            self.help_menu.setTitle(self.i18n_manager.get_translation("help"))
            self.about_action.setText(self.i18n_manager.get_translation("about"))
            self.license_action.setText(self.i18n_manager.get_translation("license"))
        except Exception:
            pass

        # Rebuild skins menu label and items
        try:
            skins_label = self.i18n_manager.get_translation("skins")
            if skins_label == "skins":
                skins_label = "Skins"
            self.skins_menu.setTitle(skins_label)
            self._populate_skins_menu()
        except Exception:
            pass

        # Refresh about and license dialogs if they are visible
        try:
            if hasattr(self, "about_dialog") and self.about_dialog.isVisible():
                self.about_dialog.refresh_text()
        except Exception:
            pass

        try:
            if hasattr(self, "license_dialog") and self.license_dialog.isVisible():
                self.license_dialog.refresh_text()
        except Exception:
            pass

    # -----------------------
    # Mouse dragging window
    # -----------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # store global position for dragging
            try:
                self.old_pos = event.globalPosition().toPoint()
            except Exception:
                # older PySide versions may not have globalPosition()
                self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None and event.buttons() & Qt.LeftButton:
            try:
                new_pos = event.globalPosition().toPoint()
            except Exception:
                new_pos = event.globalPos()
            delta = new_pos - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = new_pos

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = None


# -----------------------
# Single-instance support
# -----------------------
class SingleInstanceServer(QObject):
    activated = Signal()

    def __init__(self, server_name: str, parent=None):
        super().__init__(parent)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.WorldAccessOption)
        self.server.newConnection.connect(self.on_new_connection)

        # Clean up any stale socket file on Unix-like systems
        if os.path.exists(server_name):
            try:
                os.remove(server_name)
            except OSError:
                pass

        if not self.server.listen(server_name):
            raise RuntimeError(f"Unable to start single-instance server: {self.server.errorString()}")

    def on_new_connection(self):
        # A new instance tried to start; notify the main window.
        socket = self.server.nextPendingConnection()
        if socket is not None:
            socket.disconnectFromServer()
        self.activated.emit()


# -----------------------
# Application entry point
# -----------------------
def main() -> int:
    # suppress noisy Qt logs
    QLoggingCategory.setFilterRules(
        "qt.text.font.db=false\n"
        "qt.multimedia.ffmpeg=false\n"
        "qt.multimedia.ffmpeg.*=false\n"
    )

    if sys.platform == "win32":
        try:
            myappid = "uk.codecrafter.FancyClock"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)

    # Identify organization/app for QSettings (cross-platform persistent settings)
    QCoreApplication.setOrganizationName("OliverErnster")
    QCoreApplication.setApplicationName("FancyClock")

    # Single-instance guard (cross-platform).
    guard = SingleInstanceGuard("uk.codecrafter.FancyClock.singleton")

    if not guard.acquire():
        # Another instance is already running; notify it and exit.
        guard.notify_existing_instance()
        return 0

    # Keep guard alive for the lifetime of the app
    app.single_instance_guard = guard

    window = ClockWindow()

    # When another instance starts and connects, bring this window to the front.
    guard.activated.connect(window.bring_to_front)

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
