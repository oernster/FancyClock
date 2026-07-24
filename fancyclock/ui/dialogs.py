"""Timezone, About and Licence dialogs."""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

from fancyclock.application.localization import LocalizationService
from fancyclock.application.resources import ResourcePaths
from fancyclock.application.timezones import TimezoneService
from fancyclock.version import __version__

DIALOG_MIN_WIDTH = 450
DIALOG_MIN_HEIGHT = 400
ABOUT_ICON_PX = 96
LICENCE_BODY_HEIGHT = 520
LICENCE_MAX_WIDTH = 900

ABOUT_CREDITS = (
    ("PySide6", "Qt for Python, LGPL-3.0"),
    ("Python", "PSF licence"),
    ("pytz", "MIT"),
    ("tzlocal", "MIT"),
)

MEDIA_CREDITS = (
    (
        "Pixabay.com",
        ("olenchic", "vjthex", "TonyDias7", "AlexAntropov86", "Dulichxedap"),
    ),
    ("Pexels.com", ("Colin Jones",)),
    ("Vecteezy.com", ("Pitsanu Jaroenpipitaphorn",)),
)

LICENCE_FALLBACK_TEXT = "License file not found."


def show_timezone_dialog(parent, timezone_service: TimezoneService):
    """Timezone selection dialog with search and UTC offset display.

    Calls ``parent._change_timezone(tz_id)`` when a timezone is chosen.
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(parent.i18n_manager.get_translation("select_timezone_title"))
    dialog.setMinimumSize(DIALOG_MIN_WIDTH, DIALOG_MIN_HEIGHT)

    layout = QVBoxLayout(dialog)

    search_box = QLineEdit(dialog)
    search_box.setPlaceholderText(
        parent.i18n_manager.get_translation("search_timezone_placeholder")
    )
    layout.addWidget(search_box)

    list_widget = QListWidget(dialog)
    layout.addWidget(list_widget)

    entries = timezone_service.entries()

    for entry in entries:
        list_widget.addItem(entry.display)

    def filter_timezones(text: str):
        list_widget.clear()
        search_text = text.lower()
        for entry in entries:
            if (
                not search_text
                or search_text in entry.display.lower()
                or search_text in entry.tz_id.lower()
            ):
                list_widget.addItem(entry.display)

    search_box.textChanged.connect(filter_timezones)

    def on_item_selected(item):
        if item is None:
            return
        selected_text = item.text()
        for entry in entries:
            if entry.display == selected_text:
                parent._change_timezone(entry.tz_id)
                break
        dialog.accept()

    list_widget.itemDoubleClicked.connect(on_item_selected)

    button_layout = QHBoxLayout()

    ok_button = QPushButton(parent.i18n_manager.get_translation("ok"))
    cancel_button = QPushButton(parent.i18n_manager.get_translation("cancel"))

    ok_button.clicked.connect(
        lambda: (
            on_item_selected(list_widget.currentItem())
            if list_widget.currentItem()
            else None
        )
    )
    cancel_button.clicked.connect(dialog.reject)

    button_layout.addWidget(ok_button)
    button_layout.addWidget(cancel_button)

    layout.addLayout(button_layout)

    dialog.exec()


def _media_credits_html() -> str:
    """Render the media credits section body."""
    parts: list[str] = []
    for site, authors in MEDIA_CREDITS:
        items = "".join(f"<li>{author}</li>" for author in authors)
        parts.append(f"<p>{site}</p><ul>{items}</ul>")
    return "".join(parts)


class AboutDialog(QDialog):
    """About dialog with localized text, app icon badge and credits."""

    def __init__(
        self,
        i18n_manager: LocalizationService,
        resources: ResourcePaths,
        parent=None,
    ):
        super().__init__(parent)
        self.i18n_manager = i18n_manager
        self._resources = resources

        self.setWindowTitle(self.i18n_manager.get_translation("about_dialog_title"))
        self.setMinimumSize(DIALOG_MIN_WIDTH, DIALOG_MIN_HEIGHT)

        self.dialog_layout = QVBoxLayout(self)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(resources.about_icon_png)
        if not pixmap.isNull():
            self.icon_label.setPixmap(
                pixmap.scaled(
                    ABOUT_ICON_PX,
                    ABOUT_ICON_PX,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            self.dialog_layout.addWidget(self.icon_label)

        self.text_label = QLabel()
        self.text_label.setOpenExternalLinks(True)
        self.text_label.setWordWrap(True)
        self.dialog_layout.addWidget(self.text_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)
        self.dialog_layout.addWidget(self.button_box)

        self.refresh_text()

    def refresh_text(self):
        locale = self.i18n_manager.current_locale

        self.setWindowTitle(
            self.i18n_manager.get_translation("about_dialog_title", locale)
        )

        app_name = self.i18n_manager.get_translation("app_name", locale)
        version_label = self.i18n_manager.get_translation("version", locale)
        app_description = self.i18n_manager.get_translation("app_description", locale)
        author_label = self.i18n_manager.get_translation("author_label", locale)
        about_libs_label = self.i18n_manager.get_translation(
            "about_libraries_used", locale
        )
        credits_media_label = self.i18n_manager.get_translation("credits_media", locale)

        python_version = sys.version.split()[0]

        libraries = "".join(
            f"<li><b>{name}</b>: {licence}</li>" for name, licence in ABOUT_CREDITS
        )

        about_text = f"""
        <b>{app_name}</b>
        <p>{version_label} {__version__}</p>
        <p>{app_description}</p>
        <p><b>{author_label}</b> Oliver Ernster</p>
        <p>Python version: <b>{python_version}</b></p>
        <p><b>{about_libs_label}</b></p>
        <ul>{libraries}</ul>
        <p><b>{credits_media_label}</b></p>
        {_media_credits_html()}
        """

        self.text_label.setText(about_text)


class LicenseDialog(QDialog):
    """Licence dialog sized to the hard-wrapped licence text."""

    def __init__(
        self,
        i18n_manager: LocalizationService,
        license_path: str | None,
        parent=None,
    ):
        super().__init__(parent)
        self.i18n_manager = i18n_manager
        self._license_path = license_path

        self.setWindowTitle(self.i18n_manager.get_translation("license_dialog_title"))

        layout = QVBoxLayout(self)

        self.license_text = QTextBrowser(self)
        self.license_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.license_text.setMinimumHeight(LICENCE_BODY_HEIGHT)
        layout.addWidget(self.license_text)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.refresh_text()

    def _fitted_width(self) -> int:
        """Width that fits the hard-wrapped text, capped for pathology."""
        chrome = (
            self.license_text.verticalScrollBar().sizeHint().width()
            + 2 * self.license_text.frameWidth()
        )
        margins = self.layout().contentsMargins()
        chrome += margins.left() + margins.right()
        ideal = math.ceil(self.license_text.document().idealWidth())
        return min(ideal + chrome, LICENCE_MAX_WIDTH)

    def refresh_text(self):
        self.setWindowTitle(
            self.i18n_manager.get_translation(
                "license_dialog_title", self.i18n_manager.current_locale
            )
        )

        text = LICENCE_FALLBACK_TEXT
        if self._license_path:
            try:
                text = Path(self._license_path).read_text(encoding="utf-8")
            except Exception:
                text = LICENCE_FALLBACK_TEXT

        self.license_text.setPlainText(text)
        self.setMinimumWidth(self._fitted_width())
