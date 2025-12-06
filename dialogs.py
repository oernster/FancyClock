import pytz
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QMessageBox, QScrollArea, QLabel, QPushButton, QDialogButtonBox
from datetime import datetime
from utils import resource_path

def show_timezone_dialog(parent):
    dialog = QDialog(parent)
    dialog.setWindowTitle(parent.i18n_manager.get_translation("select_timezone_title"))
    dialog.setMinimumSize(450, 400)

    layout = QVBoxLayout()
    dialog.setLayout(layout)

    search_box = QLineEdit(dialog)
    search_box.setPlaceholderText(parent.i18n_manager.get_translation("search_timezone_placeholder"))
    layout.addWidget(search_box)

    list_widget = QListWidget(dialog)
    all_timezones = sorted(pytz.common_timezones)
    
    timezone_items = []
    now = datetime.now()
    original_locale = parent.i18n_manager.current_locale

    for tz in all_timezones:
        locale = parent._get_locale_for_timezone(tz)
        parent.i18n_manager.timezone_translator.locale = locale
        display_name = parent.i18n_manager.timezone_translator.get_display_name(tz, now)
        timezone_items.append((f"{display_name} ({tz})", tz))
    parent.i18n_manager.timezone_translator.locale = original_locale
    
    for display_text, _ in timezone_items:
        list_widget.addItem(display_text)
        
    layout.addWidget(list_widget)

    def filter_timezones(text):
        list_widget.clear()
        search_text = text.lower()
        if not text:
            for display_text, _ in timezone_items:
                list_widget.addItem(display_text)
        else:
            for display_text, tz_id in timezone_items:
                if search_text in display_text.lower() or search_text in tz_id.lower():
                    list_widget.addItem(display_text)

    search_box.textChanged.connect(filter_timezones)

    def on_item_selected(item):
        selected_text = item.text()
        for display_text, tz_id in timezone_items:
            if selected_text == display_text:
                parent._change_timezone(tz_id)
                break
        dialog.accept()

    list_widget.itemClicked.connect(on_item_selected)

    dialog.exec()

def show_license_dialog(parent):
    try:
        with open(resource_path("LICENSE"), "r", encoding="utf-8") as f:
            license_text = f.read()

        dialog = QDialog(parent)
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
        QMessageBox.critical(parent, "Error", "LICENSE file not found.")

from localization.i18n_manager import LocalizationManager

class AboutDialog(QDialog):
    def __init__(self, parent, i18n_manager: LocalizationManager):
        super().__init__(parent)
        self.i18n_manager = i18n_manager
        self.setWindowTitle(self.i18n_manager.get_translation("about_dialog_title", self.i18n_manager.current_locale))
        self.setMinimumSize(300, 200)

        self.layout = QVBoxLayout(self)
        self.text_label = QLabel(self)
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

        about_text = f"""
        <b>{self.i18n_manager.get_translation("app_name", locale)}</b>
        <p>{self.i18n_manager.get_translation("version", locale)} 1.0</p>
        <p>{self.i18n_manager.get_translation("app_description", locale)}</p>
        <p><b>{self.i18n_manager.get_translation("author_label", locale)}</b> Oliver Ernster</p>
        <p><b>{self.i18n_manager.get_translation("about_libraries_used", locale)}</b></p>
        <ul>
            <li>PySide6</li>
            <li>ntplib</li>
        </ul>
        """
        self.text_label.setText(about_text)

        # Optional: localize the OK button label (using the "ok" key)
        ok_btn = self.button_box.button(QDialogButtonBox.Ok)
        if ok_btn is not None:
            ok_btn.setText(self.i18n_manager.get_translation("ok", locale))

def show_about_dialog(parent, i18n_manager: LocalizationManager):
    if not hasattr(parent, 'about_dialog'):
        parent.about_dialog = AboutDialog(parent, i18n_manager)
    parent.about_dialog.refresh_text()
    parent.about_dialog.exec()