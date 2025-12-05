import pytz
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QMessageBox, QScrollArea, QLabel
from datetime import datetime

def show_timezone_dialog(parent):
    dialog = QDialog(parent)
    dialog.setWindowTitle("Select Timezone")
    dialog.setMinimumSize(300, 400)

    layout = QVBoxLayout()
    dialog.setLayout(layout)

    search_box = QLineEdit(dialog)
    search_box.setPlaceholderText("Search for a timezone...")
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
        with open(parent.resource_path("LICENSE"), "r", encoding="utf-8") as f:
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

def show_about_dialog(parent):
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
    QMessageBox.about(parent, "About Simple Clock", about_text)