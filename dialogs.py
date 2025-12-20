import sys
from datetime import datetime

import pytz
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QWidget,
    QLabel,
    QDialogButtonBox,
)

from utils import resource_path
from version import __version__  # <- centralised version import


def show_timezone_dialog(parent):
    """
    Timezone selection dialog with search and UTC offset display.
    Calls parent._change_timezone(tz_id) when a timezone is chosen.
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(parent.i18n_manager.get_translation("select_timezone_title"))
    dialog.setMinimumSize(450, 400)

    layout = QVBoxLayout(dialog)

    # Search box
    search_box = QLineEdit(dialog)
    search_box.setPlaceholderText(
        parent.i18n_manager.get_translation("search_timezone_placeholder")
    )
    layout.addWidget(search_box)

    # List of timezones
    list_widget = QListWidget(dialog)
    layout.addWidget(list_widget)

    timezones = pytz.all_timezones
    timezone_items = []

    # current UTC time with tzinfo
    current_utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)

    for tz in timezones:
        tz_obj = pytz.timezone(tz)
        local_time = current_utc_time.astimezone(tz_obj)

        # IMPORTANT: ask the datetime for its offset, not tz_obj.utcoffset(local_time)
        offset = local_time.utcoffset()
        if offset is None:
            offset_seconds = 0
        else:
            offset_seconds = offset.total_seconds()

        offset_hours = offset_seconds / 3600
        offset_str = f"UTC{offset_hours:+.1f}"
        display_text = f"[{offset_str}] {tz}"
        timezone_items.append((display_text, tz))

    # Sort by display text
    timezone_items.sort(key=lambda x: x[0])

    for display_text, _ in timezone_items:
        list_widget.addItem(display_text)

    def filter_timezones(text: str):
        list_widget.clear()
        search_text = text.lower()
        if not text:
            for display_text, _ in timezone_items:
                list_widget.addItem(display_text)
            return

        for display_text, tz_id in timezone_items:
            if search_text in display_text.lower() or search_text in tz_id.lower():
                list_widget.addItem(display_text)

    search_box.textChanged.connect(filter_timezones)

    def on_item_selected(item):
        if item is None:
            return
        selected_text = item.text()
        for display_text, tz_id in timezone_items:
            if display_text == selected_text:
                parent._change_timezone(tz_id)
                break
        dialog.accept()

    list_widget.itemDoubleClicked.connect(on_item_selected)

    # Buttons
    button_layout = QHBoxLayout()

    ok_button = QPushButton(parent.i18n_manager.get_translation("ok"))
    cancel_button = QPushButton(parent.i18n_manager.get_translation("cancel"))

    ok_button.clicked.connect(
        lambda: on_item_selected(list_widget.currentItem())
        if list_widget.currentItem()
        else None
    )
    cancel_button.clicked.connect(dialog.reject)

    button_layout.addWidget(ok_button)
    button_layout.addWidget(cancel_button)

    layout.addLayout(button_layout)

    dialog.exec()


class AboutDialog(QDialog):
    """
    About dialog with localized text and media credits.
    """

    def __init__(self, i18n_manager, parent=None):
        super().__init__(parent)
        self.i18n_manager = i18n_manager

        self.setWindowTitle(self.i18n_manager.get_translation("about_dialog_title"))
        self.setMinimumSize(450, 400)

        self.layout = QVBoxLayout(self)
        self.text_label = QLabel()
        self.text_label.setOpenExternalLinks(True)
        self.text_label.setWordWrap(True)
        self.layout.addWidget(self.text_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)
        self.layout.addWidget(self.button_box)

        self.refresh_text()

    def refresh_text(self):
        locale = self.i18n_manager.current_locale

        # Update window title from JSON on each refresh
        self.setWindowTitle(
            self.i18n_manager.get_translation("about_dialog_title", locale)
        )

        app_name = self.i18n_manager.get_translation("app_name", locale)
        version_label = self.i18n_manager.get_translation("version", locale)
        app_description = self.i18n_manager.get_translation(
            "app_description", locale
        )
        author_label = self.i18n_manager.get_translation("author_label", locale)
        about_libs_label = self.i18n_manager.get_translation(
            "about_libraries_used", locale
        )
        credits_media_label = self.i18n_manager.get_translation(
            "credits_media", locale
        )

        python_version = sys.version.split()[0]

        about_text = f"""
        <b>{app_name}</b>
        <p>{version_label} {__version__}</p>
        <p>{app_description}</p>
        <p><b>{author_label}</b> Oliver Ernster</p>
        <p>Python version: <b>{python_version}</b></p>
        <p><b>{about_libs_label}</b></p>
        <ul>
            <li>PySide6</li>
            <li>ntplib</li>
        </ul>
        <p><b>{credits_media_label}</b></p>
        <p>Pixabay.com</p>
        <ul>
            <li>olenchic</li>
            <li>vjthex</li>
            <li>TonyDias7</li>
            <li>AlexAntropov86</li>
            <li>Dulichxedap</li>
        </ul>
        <p>Pexels.com</p>
        <ul>
            <li>Colin Jones</li>
        </ul>
        <p>Vecteezy.com</p>
        <ul>
            <li>Pitsanu Jaroenpipitaphorn</li>
        </ul>
        """

        self.text_label.setText(about_text)


class LicenseDialog(QDialog):
    """
    License dialog that loads LICENSE.txt via resource_path and shows it
    in a scrollable, selectable text area.
    """

    def __init__(self, i18n_manager, parent=None):
        super().__init__(parent)
        self.i18n_manager = i18n_manager

        self.setWindowTitle(
            self.i18n_manager.get_translation("license_dialog_title")
        )
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        scroll_content = QWidget(scroll_area)
        scroll_layout = QVBoxLayout(scroll_content)

        self.license_text = QLabel()
        self.license_text.setWordWrap(True)
        self.license_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        scroll_layout.addWidget(self.license_text)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.refresh_text()

    def refresh_text(self):
        locale = self.i18n_manager.current_locale

        # Localized window title
        self.setWindowTitle(
            self.i18n_manager.get_translation("license_dialog_title", locale)
        )

        # Try LICENSE first, then LICENSE.txt
        possible_files = ["LICENSE", "LICENSE.txt"]

        license_text = None

        for fname in possible_files:
            try:
                path = resource_path(fname)
                with open(path, "r", encoding="utf-8") as f:
                    license_text = f.read()
                    break
            except Exception:
                continue

        if not license_text:
            license_text = "License file not found."

        self.license_text.setText(license_text)
