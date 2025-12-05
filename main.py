import sys
import os
import ctypes
import pytz
import re
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QLabel, QMessageBox, QSizePolicy, QScrollArea, QDialog, QLineEdit, QListWidget
from PySide6.QtCore import QTimer, QTime, QDateTime, Qt, QPoint, QPropertyAnimation, QEasingCurve, QTimeZone
from PySide6.QtGui import QIcon, QAction
from analog_clock import AnalogClock
from digital_clock import DigitalClock
from ntp_client import NTPClient
from datetime import datetime, timezone
from localization.i18n_manager import I18nManager

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller. """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ClockWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fancy Clock")
        self.setWindowFlags(Qt.Window)
        self.setWindowIcon(QIcon(resource_path("clock.ico")))
        self.resize(400, 440)

        self.i18n_manager = I18nManager()
        self._create_menu_bar()
        self.ntp_client = NTPClient()
        self.time_offset = 0
        self.time_zone = QTimeZone.systemTimeZone()
        self.synchronize_time()
        self.old_pos = None
        self.tz_locale_map = {
            "Europe/London": "en_GB",
            "Europe/Paris": "fr_FR",
            "Europe/Berlin": "de_DE",
            "America/New_York": "en_US",
            "Asia/Tokyo": "ja_JP",
            "Asia/Dubai": "ar_SA",
            "Asia/Kolkata": "hi_IN",
        }

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
        self.timezone_action.triggered.connect(self._show_timezone_dialog)
        menu_bar.addAction(self.timezone_action)

        self.help_menu = menu_bar.addMenu(self.i18n_manager.get_translation("help", default="&Help"))
        self.about_action = QAction(self.i18n_manager.get_translation("about", default="&About"), self)
        self.about_action.triggered.connect(self._show_about_dialog)
        self.help_menu.addAction(self.about_action)

        self.license_action = QAction(self.i18n_manager.get_translation("license", default="&License"), self)
        self.license_action.triggered.connect(self._show_license_dialog)
        self.help_menu.addAction(self.license_action)

    def _show_license_dialog(self):
        try:
            with open(resource_path("LICENSE"), "r", encoding="utf-8") as f:
                license_text = f.read()

            dialog = QDialog(self)
            dialog.setWindowTitle("License")
            dialog.resize(600, 600)

            layout = QVBoxLayout(dialog)
            scroll_area = QScrollArea(dialog)
            scroll_area.setWidgetResizable(True)
            
            label = QLabel(license_text, dialog)
            label.setWordWrap(True)
            
            scroll_area.setWidget(label)
            layout.addWidget(scroll_area)
            dialog.setLayout(layout)
            
            dialog.exec()

        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "LICENSE file not found.")

    def _show_about_dialog(self):
        about_text = """
        <b>Simple Clock</b>
        <p>Version 1.0</p>
        <p>A beautiful but simple clock application.</p>
        <p><b>Author:</b> Oliver Ernster</p>
        <p><b>Modules Used:</b></p>
        <ul>
            <li>PySide6</li>
            <li>ntplib</li>
        </ul>
        """
        QMessageBox.about(self, "About Simple Clock", about_text)

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

    def _show_timezone_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Timezone")
        dialog.setMinimumSize(300, 400)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        search_box = QLineEdit(dialog)
        search_box.setPlaceholderText("Search for a timezone...")
        layout.addWidget(search_box)

        list_widget = QListWidget(dialog)
        all_timezones = sorted(pytz.common_timezones)
        list_widget.addItems(all_timezones)
        layout.addWidget(list_widget)

        def filter_timezones(text):
            list_widget.clear()
            if not text:
                list_widget.addItems(all_timezones)
            else:
                filtered_timezones = []
                search_text = text.lower()
                for tz in all_timezones:
                    if search_text in tz.lower():
                        filtered_timezones.append(tz)
                list_widget.addItems(filtered_timezones)

        search_box.textChanged.connect(filter_timezones)

        def on_item_selected(item):
            self._change_timezone(item.text())
            dialog.accept()

        list_widget.itemClicked.connect(on_item_selected)

        dialog.exec()


    def _change_timezone(self, tz):
        self.time_zone = QTimeZone(tz.encode('utf-8'))
        locale = self.tz_locale_map.get(tz, "en_GB")
        self.i18n_manager.set_locale(locale)
        self.update_time()
        self.update_menu_text()

    def update_menu_text(self):
        self.timezone_action.setText(self.i18n_manager.get_translation("timezone", default="&Timezone"))
        self.help_menu.setTitle(self.i18n_manager.get_translation("help", default="&Help"))
        self.about_action.setText(self.i18n_manager.get_translation("about", default="&About"))
        self.license_action.setText(self.i18n_manager.get_translation("license", default="&License"))

if __name__ == "__main__":
    # This Windows-specific call is essential for the taskbar icon to work correctly.
    myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    window = ClockWindow()
    window.show()
    sys.exit(app.exec())
