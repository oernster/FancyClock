"""The persistent summary of alarms that were missed."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fancyclock.domain.alarms import color_hex
from fancyclock.ui.alarms.formatting import color_dot_icon, occurrence_text

DIALOG_MIN_WIDTH = 420
DIALOG_MIN_HEIGHT = 260


def show_missed_dialog(parent: QWidget | None, i18n, missed) -> None:
    """Show the missed-alarms summary; ``missed`` is MissedAlarm entries."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(i18n.get_translation("missed_alarms_title"))
    dialog.setMinimumSize(DIALOG_MIN_WIDTH, DIALOG_MIN_HEIGHT)

    layout = QVBoxLayout(dialog)
    total = sum(entry.missed_count for entry in missed)
    text = i18n.get_translation("missed_alarms_text")
    layout.addWidget(QLabel(text.format(count=total), dialog))

    listing = QListWidget(dialog)
    for entry in missed:
        when = occurrence_text(
            i18n, entry.occurrence_utc, entry.occurrence_utc.astimezone().tzinfo
        )
        label = entry.alarm.label or "-"
        line = f"{when}   {label}"
        if entry.missed_count > 1:
            times = i18n.get_translation("times_missed")
            line = f"{line}   {times.format(count=entry.missed_count)}"
        listing.addItem(
            QListWidgetItem(color_dot_icon(color_hex(entry.alarm.color)), line)
        )
    layout.addWidget(listing)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)

    dialog.exec()
