"""Modal timezone picker returning the chosen identifier."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QListWidget,
    QVBoxLayout,
)

PICKER_MIN_WIDTH = 450
PICKER_MIN_HEIGHT = 400


def pick_timezone(parent, i18n, timezone_service) -> str | None:
    """Show the searchable timezone list; return a tz id or ``None``."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(i18n.get_translation("select_timezone_title"))
    dialog.setMinimumSize(PICKER_MIN_WIDTH, PICKER_MIN_HEIGHT)

    layout = QVBoxLayout(dialog)
    search_box = QLineEdit(dialog)
    search_box.setPlaceholderText(i18n.get_translation("search_timezone_placeholder"))
    layout.addWidget(search_box)

    list_widget = QListWidget(dialog)
    layout.addWidget(list_widget)

    entries = timezone_service.entries()
    by_display = {entry.display: entry.tz_id for entry in entries}

    def repopulate(text: str) -> None:
        list_widget.clear()
        needle = text.lower()
        for entry in entries:
            if (
                not needle
                or needle in entry.display.lower()
                or needle in entry.tz_id.lower()
            ):
                list_widget.addItem(entry.display)

    repopulate("")
    search_box.textChanged.connect(repopulate)
    list_widget.itemDoubleClicked.connect(lambda _item: dialog.accept())

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    current = list_widget.currentItem()
    if current is None:
        return None
    return by_display.get(current.text())
