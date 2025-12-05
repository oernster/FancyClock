import sys
import os
import ctypes
import json
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSizePolicy
from PySide6.QtCore import QTimer, QDateTime, Qt, QPropertyAnimation, QEasingCurve, QTimeZone, QLoggingCategory
from PySide6.QtGui import QIcon, QAction
from analog_clock import AnalogClock
from digital_clock import DigitalClock
from ntp_client import NTPClient
from datetime import datetime, timezone
from localization.i18n_manager import I18nManager
from utils import resource_path
from dialogs import show_timezone_dialog, show_license_dialog, show_about_dialog

class ClockWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fancy Clock")
        self.setWindowFlags(Qt.Window)
        self.setWindowIcon(QIcon(resource_path("clock.ico")))
        self.resize(400, 440)

        self.i18n_manager = I18nManager()
        self.i18n_manager.set_locale(self.i18n_manager.detect_system_locale())
        self._load_tz_locale_map()
        self._create_menu_bar()
        self.ntp_client = NTPClient()
        self.time_offset = 0
        self.time_zone = QTimeZone.systemTimeZone()
        self.synchronize_time()
        self.old_pos = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.analog_clock = AnalogClock(self, i18n_manager=self.i18n_manager)
        self.layout.addWidget(self.analog_clock)
        self.layout.addSpacing(10)
        self.digital_clock = DigitalClock(self)
        self.digital_clock.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layout.addWidget(self.digital_clock)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(16) # ~60 FPS

        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
    def _load_tz_locale_map(self):
        try:
            with open(resource_path("timezone_locale_map.json"), "r", encoding="utf-8") as f:
                self.tz_locale_map = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.tz_locale_map = {}

    def show(self):
        super().show()
        self.animation.start()

    def synchronize_time(self):
        ntp_time = self.ntp_client.get_time()
        local_time = datetime.now(timezone.utc)
        self.time_offset = (ntp_time - local_time).total_seconds()

    def get_current_time(self):
        current_time = QDateTime.currentDateTimeUtc().addSecs(int(self.time_offset))
        return current_time.toTimeZone(self.time_zone)

    def update_time(self):
        current_date_time = self.get_current_time()
        self.analog_clock.time = current_date_time
        self.digital_clock.time = current_date_time
        self.analog_clock.repaint()
        self.digital_clock.show_time()

    def update_animation(self):
        self.analog_clock.update_stars()
        self.digital_clock.update_stars()
        self.analog_clock.repaint()
        self.digital_clock.repaint()

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        menu_bar.addMenu("").addAction(QAction("", self)) # This is a dummy menu
        menu_bar.setCornerWidget(spacer)

        self.timezone_action = QAction(self.i18n_manager.get_translation("timezone", default="&Timezone"), self)
        self.timezone_action.triggered.connect(lambda: show_timezone_dialog(self))
        menu_bar.addAction(self.timezone_action)

        self.help_menu = menu_bar.addMenu(self.i18n_manager.get_translation("help", default="&Help"))
        self.about_action = QAction(self.i18n_manager.get_translation("about", default="&About"), self)
        self.about_action.triggered.connect(lambda: show_about_dialog(self))
        self.help_menu.addAction(self.about_action)

        self.license_action = QAction(self.i18n_manager.get_translation("license", default="&License"), self)
        self.license_action.triggered.connect(lambda: show_license_dialog(self))
        self.help_menu.addAction(self.license_action)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None and event.buttons() == Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def _get_locale_for_timezone(self, tz_id):
        """Get the most appropriate locale for a given timezone."""
        return self.tz_locale_map.get(tz_id, "en_US") # Default to en_US for unknown
    
    def _change_timezone(self, tz):
        self.time_zone = QTimeZone(tz.encode('utf-8'))
        # Auto-detect and set locale based on timezone if a mapping exists
        if tz in self.tz_locale_map:
            locale = self.tz_locale_map.get(tz)
            if locale:
                self.i18n_manager.set_locale(locale)
        
        self.update_time()
        self.update_menu_text(locale)

    def update_menu_text(self, locale=None):
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


def main():
    # Suppress Qt font warnings
    QLoggingCategory.setFilterRules("qt.text.font.db=false")
    
    # This Windows-specific call is essential for the taskbar icon to work correctly.
    if sys.platform == "win32":
        myappid = 'mycompany.myproduct.subproduct.version'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    
    # Use system fonts - no custom font loading needed
    
    window = ClockWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()