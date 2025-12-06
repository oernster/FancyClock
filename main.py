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
    QGuiApplication,
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
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from analog_clock import AnalogClock
from digital_clock import DigitalClock
from ntp_client import NTPClient
from localization.i18n_manager import LocalizationManager
from utils import resource_path
from dialogs import show_timezone_dialog, show_license_dialog, show_about_dialog


class SingleInstanceGuard(QObject):
    """
    Cross-platform single-instance guard using QSystemSemaphore + QSharedMemory
    plus a QLocalServer/QLocalSocket channel so secondary instances can
    request that the primary instance brings its window to the front.
    """

    activated = Signal()  # emitted in the *primary* instance when a
                          # secondary instance asks to be brought to front

    def __init__(self, key: str, parent: QObject | None = None):
        super().__init__(parent)
        self._key = key
        self._sem = None
        self._mem = None
        self._is_primary = False
        self._server: QLocalServer | None = None
        self._init_ipc()

    # ------------------ public API ------------------

    @property
    def is_primary(self) -> bool:
        """True if this process is the first (owning) instance."""
        return self._is_primary

    def release(self) -> None:
        """Explicitly release the shared memory segment."""
        if not self._is_primary:
            return

        self._sem.acquire()
        try:
            if self._mem.isAttached():
                self._mem.detach()
        finally:
            self._sem.release()

        self._is_primary = False

        if self._server is not None:
            self._server.close()
            self._server = None

    # Called in a *secondary* instance to tell primary to activate its window.
    def notify_primary_to_activate(self) -> None:
        if self._is_primary:
            return  # nothing to do – we *are* primary

        socket = QLocalSocket()
        # Same key as the server listens on:
        socket.connectToServer(self._key)
        if not socket.waitForConnected(250):
            socket.abort()
            return

        try:
            # We don’t really care about payload; a single byte is enough.
            socket.write(b"activate")
            socket.flush()
            socket.waitForBytesWritten(250)
        finally:
            socket.disconnectFromServer()
            socket.close()

    # Context manager support (RAII-ish)
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def __del__(self):
        try:
            self.release()
        except Exception:
            pass

    # ------------------ internals ------------------

    def _init_ipc(self) -> None:
        # Separate semaphore key to avoid collisions
        sem_key = f"{self._key}_sem"

        self._sem = QSystemSemaphore(sem_key, 1)
        self._mem = QSharedMemory(self._key)

        # Serialize operations on shared memory
        self._sem.acquire()
        try:
            # If a segment already exists and we can attach, another instance is running.
            if self._mem.attach():
                self._mem.detach()
                self._is_primary = False
                return

            # No existing segment – create a 1-byte block just to mark presence.
            if not self._mem.create(1):
                self._is_primary = False
                return

            self._is_primary = True
        finally:
            self._sem.release()

        # If we are primary, also start a local server to listen for
        # “please activate” requests from secondary instances.
        if self._is_primary:
            self._start_server()

    def _start_server(self) -> None:
        # Clean up any stale server with the same name.
        try:
            QLocalServer.removeServer(self._key)
        except Exception:
            pass

        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)

        if not self._server.listen(self._key):
            # If listening fails, we still have single-instance behaviour,
            # just no “raise existing” support.
            self._server = None

    def _on_new_connection(self) -> None:
        if self._server is None:
            return
        socket = self._server.nextPendingConnection()
        if socket is None:
            return

        # Read & discard payload; we only care that *someone* connected.
        socket.readAll()
        socket.disconnectFromServer()
        socket.close()

        # Tell whoever is interested (main window) to bring itself to front.
        self.activated.emit()


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
        if self.windowState() & Qt.WindowMinimized:
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized)

        # Make sure it’s the active window in the stack
        self.raise_()
        self.activateWindow()

    def show(self):
        super().show()
        if self.animation is not None:
            self.animation.start()

    # -----------------------
    # Window sizing & show
    # -----------------------
    def _set_scaled_initial_size(self, scale: float = 1.5):
        base_w, base_h = 400, 440
        self.resize(int(base_w * scale), int(base_h * scale))

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
            self.time_offset = (ntp_time - local_utc_now).total_seconds()

    def get_current_time(self) -> QDateTime:
        """
        Return a QDateTime adjusted using the NTP offset and the selected timezone.
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

    def _supports_window_opacity(self) -> bool:
        name = QGuiApplication.platformName().lower()
        # Known platforms that support windowOpacity
        return any(key in name for key in ("windows", "xcb", "cocoa"))

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

        # Backwards-compatible names
        for name in ("update_galaxy", "update_stars"):
            if hasattr(clock_widget, name) and callable(getattr(clock_widget, name)):
                try:
                    getattr(clock_widget, name)()
                    return
                except Exception:
                    pass

        # If nothing else, just request an update (may be cheap)
        try:
            clock_widget.update()
        except Exception:
            try:
                clock_widget.repaint()
            except Exception:
                pass

    # -----------------------
    # Timers' slots
    # -----------------------
    def update_time(self):
        """
        Called once per second. Update both clocks' time.
        """
        current_qdt = self.get_current_time()
        # update analog and digital in a safe robust way
        self._tick_clock(self.analog_clock, current_qdt)
        self._tick_clock(self.digital_clock, current_qdt)

    def update_animation(self):
        """
        Called frequently (~60 FPS). Advance animations for both clocks.
        """
        self._animate_clock(self.analog_clock)
        self._animate_clock(self.digital_clock)

    # -----------------------
    # Menu / UI
    # -----------------------
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

        # Help menu with About and License
        self.help_menu = menu_bar.addMenu(self.i18n_manager.get_translation("help"))

        self.about_action = QAction(self.i18n_manager.get_translation("about"), self)
        self.about_action.triggered.connect(lambda: show_about_dialog(self, self.i18n_manager))
        self.help_menu.addAction(self.about_action)

        self.license_action = QAction(self.i18n_manager.get_translation("license"), self)
        self.license_action.triggered.connect(lambda: show_license_dialog(self))
        self.help_menu.addAction(self.license_action)

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
        try:
            if self.old_pos is not None and event.buttons() == Qt.LeftButton:
                try:
                    new_pos = event.globalPosition().toPoint()
                except Exception:
                    new_pos = event.globalPos()
                delta = new_pos - self.old_pos
                self.move(self.pos() + delta)
                self.old_pos = new_pos
        except Exception:
            pass

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    # -----------------------
    # Timezone / Locale helpers
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
        """
        Public hook called by the timezone dialog (pass tz as timezone id string).
        This will update the QTimeZone used, set the i18n locale, and retranslate UI.
        """
        try:
            self.time_zone = QTimeZone(tz.encode("utf-8"))
        except Exception:
            # if invalid tz id, ignore
            pass

        locale = self._get_locale_for_timezone(tz)
        try:
            if locale:
                self.i18n_manager.set_locale(locale)
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

        # Update menu text (preserve behavior of previous implementation)
        try:
            self.update_menu_text()
        except Exception:
            pass

        # Let clocks re-fetch any localized strings if they choose to
        try:
            if hasattr(self.digital_clock, "update_localization"):
                self.digital_clock.update_localization()
        except Exception:
            pass

        try:
            if hasattr(self.analog_clock, "update_localization"):
                self.analog_clock.update_localization()
        except Exception:
            pass

    def update_menu_text(self, locale=None):
        """
        Update menu labels. If 'locale' is provided, request translations for that locale.
        """
        try:
            if locale:
                self.timezone_action.setText(self.i18n_manager.get_translation("timezone", locale=locale))
                self.help_menu.setTitle(self.i18n_manager.get_translation("help", locale=locale))
                self.about_action.setText(self.i18n_manager.get_translation("about", locale=locale))
                self.license_action.setText(self.i18n_manager.get_translation("license", locale=locale))
            else:
                self.timezone_action.setText(self.i18n_manager.get_translation("timezone"))
                self.help_menu.setTitle(self.i18n_manager.get_translation("help"))
                self.about_action.setText(self.i18n_manager.get_translation("about"))
                self.license_action.setText(self.i18n_manager.get_translation("license"))
        except Exception:
            pass

def main() -> int:
    # suppress noisy Qt font db warnings
    QLoggingCategory.setFilterRules("qt.text.font.db=false")

    if sys.platform == "win32":
        try:
            myappid = "uk.codecrafter.FancyClock"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)

    # Single-instance guard (cross-platform).
    guard = SingleInstanceGuard("uk.codecrafter.FancyClock.singleton")

    if not guard.is_primary:
        # Instead of showing a dialog, ask the primary instance to activate its window
        guard.notify_primary_to_activate()
        return 0

    # Keep the guard alive for the lifetime of the app.
    app.single_instance_guard = guard

    window = ClockWindow()

    # When another instance starts and connects, bring this window to the front.
    guard.activated.connect(window.bring_to_front)

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
