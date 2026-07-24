"""The alarms manager dialog: list, master switch, volume, import/export."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from fancyclock.domain.alarms import AlarmError, color_hex
from fancyclock.ui.alarms.editor_dialog import AlarmEditorDialog
from fancyclock.ui.alarms.formatting import color_dot_icon, days_text, time_text

DIALOG_MIN_WIDTH = 560
DIALOG_MIN_HEIGHT = 460
VOLUME_SLIDER_STEPS = 100
JSON_FILE_FILTER = "JSON (*.json)"
ALARM_ID_ROLE = Qt.ItemDataRole.UserRole


class AlarmManagerDialog(QDialog):
    """Lists alarms and hosts the editor, master switch and volume."""

    def __init__(
        self,
        i18n,
        alarm_service,
        settings,
        timezone_service,
        sound_player,
        default_tz_id: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._service = alarm_service
        self._settings = settings
        self._timezone_service = timezone_service
        self._sound_player = sound_player
        self._default_tz_id = default_tz_id

        self.setWindowTitle(i18n.get_translation("alarms_title"))
        self.setMinimumSize(DIALOG_MIN_WIDTH, DIALOG_MIN_HEIGHT)

        layout = QVBoxLayout(self)

        self._master_check = QCheckBox(
            i18n.get_translation("alarms_enabled_master"), self
        )
        self._master_check.setChecked(alarm_service.master_enabled())
        self._master_check.toggled.connect(alarm_service.set_master_enabled)
        layout.addWidget(self._master_check)

        self._next_label = QLabel(self)
        layout.addWidget(self._next_label)

        self._list = QListWidget(self)
        self._list.itemDoubleClicked.connect(lambda _item: self._edit())
        self._list.itemChanged.connect(self._item_check_changed)
        layout.addWidget(self._list)

        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel(i18n.get_translation("alarm_volume"), self))
        self._volume = QSlider(Qt.Orientation.Horizontal, self)
        self._volume.setRange(0, VOLUME_SLIDER_STEPS)
        self._volume.setValue(round(settings.alarm_volume() * VOLUME_SLIDER_STEPS))
        self._volume.valueChanged.connect(
            lambda value: settings.set_alarm_volume(value / VOLUME_SLIDER_STEPS)
        )
        volume_row.addWidget(self._volume)
        layout.addLayout(volume_row)

        buttons_row = QHBoxLayout()
        for key, handler in (
            ("alarm_new", self._new),
            ("alarm_edit", self._edit),
            ("alarm_delete", self._delete),
            ("alarm_import", self._import),
            ("alarm_export", self._export),
        ):
            button = QPushButton(i18n.get_translation(key), self)
            button.clicked.connect(handler)
            buttons_row.addWidget(button)
        buttons_row.addStretch()
        layout.addLayout(buttons_row)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)

        self.refresh()

    # ------------------------------------------------------------------
    # List handling
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Rebuild the alarm list and the next-alarm line."""
        self._list.blockSignals(True)
        self._list.clear()
        for alarm in self._service.alarms():
            time_part = time_text(self._i18n, alarm.hour, alarm.minute)
            label_part = alarm.label or "-"
            days_part = days_text(self._i18n, alarm)
            item = QListWidgetItem(
                color_dot_icon(color_hex(alarm.color)),
                f"{time_part}   {label_part}   {days_part}",
            )
            item.setData(ALARM_ID_ROLE, alarm.alarm_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if alarm.enabled else Qt.CheckState.Unchecked
            )
            self._list.addItem(item)
        self._list.blockSignals(False)

        info = self._service.next_alarm()
        prefix = self._i18n.get_translation("alarm_next")
        if info is None:
            self._next_label.setText(self._i18n.get_translation("alarm_none"))
        else:
            when = time_text(
                self._i18n,
                info.occurrence_utc.astimezone().hour,
                info.occurrence_utc.astimezone().minute,
            )
            label = info.alarm.label or "-"
            self._next_label.setText(f"{prefix}: {when} {label}")

    def _selected_alarm_id(self) -> str | None:
        item = self._list.currentItem()
        return item.data(ALARM_ID_ROLE) if item else None

    def _item_check_changed(self, item: QListWidgetItem) -> None:
        alarm_id = item.data(ALARM_ID_ROLE)
        enabled = item.checkState() == Qt.CheckState.Checked
        self._service.set_enabled(alarm_id, enabled)
        self.refresh()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _new(self) -> None:
        dialog = AlarmEditorDialog(
            self._i18n,
            self._timezone_service,
            self._sound_player,
            alarm_id=self._service.new_alarm_id(),
            default_tz_id=self._default_tz_id,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._service.upsert(dialog.result_alarm())
            self.refresh()

    def _edit(self) -> None:
        alarm_id = self._selected_alarm_id()
        alarm = self._service.alarm_by_id(alarm_id) if alarm_id else None
        if alarm is None:
            return
        dialog = AlarmEditorDialog(
            self._i18n,
            self._timezone_service,
            self._sound_player,
            alarm_id=alarm.alarm_id,
            default_tz_id=self._default_tz_id,
            alarm=alarm,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._service.upsert(dialog.result_alarm())
            self.refresh()

    def _delete(self) -> None:
        alarm_id = self._selected_alarm_id()
        alarm = self._service.alarm_by_id(alarm_id) if alarm_id else None
        if alarm is None:
            return
        text = self._i18n.get_translation("alarm_delete_confirm_text")
        answer = QMessageBox.question(
            self,
            self._i18n.get_translation("alarm_delete_confirm_title"),
            text.format(label=alarm.label or "-"),
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Ok:
            self._service.delete(alarm.alarm_id)
            self.refresh()

    def _import(self) -> None:
        path, _selected = QFileDialog.getOpenFileName(
            self, self._i18n.get_translation("alarm_import"), "", JSON_FILE_FILTER
        )
        if not path:
            return
        try:
            count = self._service.import_alarms(Path(path))
        except AlarmError as error:
            QMessageBox.warning(
                self,
                self._i18n.get_translation("alarm_import_failed"),
                str(error),
            )
            return
        text = self._i18n.get_translation("alarm_import_done")
        QMessageBox.information(self, self.windowTitle(), text.format(count=count))
        self.refresh()

    def _export(self) -> None:
        path, _selected = QFileDialog.getSaveFileName(
            self, self._i18n.get_translation("alarm_export"), "", JSON_FILE_FILTER
        )
        if not path:
            return
        count = self._service.export_alarms(Path(path))
        text = self._i18n.get_translation("alarm_export_done")
        QMessageBox.information(self, self.windowTitle(), text.format(count=count))
