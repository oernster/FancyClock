"""The alarm editor dialog: create or edit one alarm."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QButtonGroup,
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from fancyclock.domain.alarms import (
    ALARM_COLORS,
    DEFAULT_SNOOZE_MINUTES,
    SNOOZE_LIMIT_PRESETS,
    SNOOZE_PRESET_MINUTES,
    SOUND_NAMES,
    Alarm,
)
from fancyclock.ui.alarms.formatting import WEEKDAY_KEYS, duration_text
from fancyclock.ui.alarms.time_picker import TimePicker
from fancyclock.ui.alarms.tz_picker import pick_timezone

SWATCH_SIZE_PX = 28
DAY_CHIP_MIN_WIDTH_PX = 44
PREVIEW_VOLUME = 0.6


def _swatch_style(hex_value: str, selected: bool) -> str:
    border = "#f2f4f8" if selected else "transparent"
    return (
        f"QPushButton {{ background-color: {hex_value};"
        f" border: 2px solid {border}; border-radius: 6px; }}"
    )


class AlarmEditorDialog(QDialog):
    """Edits every field of one alarm; OK yields ``result_alarm()``."""

    def __init__(
        self,
        i18n,
        timezone_service,
        sound_player,
        alarm_id: str,
        default_tz_id: str,
        alarm: Alarm | None = None,
        default_time: tuple[int, int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._timezone_service = timezone_service
        self._sound_player = sound_player
        self._alarm_id = alarm_id
        self._tz_id = alarm.tz_id if alarm else default_tz_id

        title_key = "alarm_editor_title_edit" if alarm else "alarm_editor_title_new"
        self.setWindowTitle(i18n.get_translation(title_key))

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self._label_edit = QLineEdit(self)
        form.addRow(i18n.get_translation("alarm_label"), self._label_edit)

        self._time_picker = TimePicker(self)
        form.addRow(i18n.get_translation("alarm_time"), self._time_picker)

        self._repeat_radio = QRadioButton(
            i18n.get_translation("alarm_repeat_weekly"), self
        )
        self._one_off_radio = QRadioButton(i18n.get_translation("alarm_one_off"), self)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self._repeat_radio)
        mode_row.addWidget(self._one_off_radio)
        mode_row.addStretch()
        form.addRow("", _wrap(mode_row, self))

        self._day_chips: list[QPushButton] = []
        days_row = QHBoxLayout()
        for key in WEEKDAY_KEYS:
            chip = QPushButton(i18n.get_translation(key), self)
            chip.setCheckable(True)
            chip.setMinimumWidth(DAY_CHIP_MIN_WIDTH_PX)
            chip.toggled.connect(self._validate)
            days_row.addWidget(chip)
            self._day_chips.append(chip)
        self._days_widget = _wrap(days_row, self)
        form.addRow("", self._days_widget)

        self._calendar = QCalendarWidget(self)
        self._calendar.setMinimumDate(QDate.currentDate())
        form.addRow("", self._calendar)

        tz_row = QHBoxLayout()
        self._tz_label = QLabel(self._tz_id, self)
        tz_button = QPushButton(i18n.get_translation("timezone"), self)
        tz_button.clicked.connect(self._change_timezone)
        tz_row.addWidget(self._tz_label)
        tz_row.addStretch()
        tz_row.addWidget(tz_button)
        form.addRow(i18n.get_translation("alarm_timezone"), _wrap(tz_row, self))

        self._color_group = QButtonGroup(self)
        self._color_group.setExclusive(True)
        colors_row = QHBoxLayout()
        self._color_buttons: dict[str, QPushButton] = {}
        for name, hex_value in ALARM_COLORS:
            swatch = QPushButton(self)
            swatch.setCheckable(True)
            swatch.setFixedSize(SWATCH_SIZE_PX, SWATCH_SIZE_PX)
            swatch.setToolTip(name)
            swatch.toggled.connect(lambda _checked: self._restyle_swatches())
            self._color_group.addButton(swatch)
            colors_row.addWidget(swatch)
            self._color_buttons[name] = swatch
        colors_row.addStretch()
        form.addRow(i18n.get_translation("alarm_color"), _wrap(colors_row, self))

        sound_row = QHBoxLayout()
        self._sound_combo = QComboBox(self)
        for name in SOUND_NAMES:
            self._sound_combo.addItem(i18n.get_translation(f"sound_{name}"), name)
        preview = QPushButton(i18n.get_translation("alarm_preview"), self)
        preview.clicked.connect(self._preview_sound)
        sound_row.addWidget(self._sound_combo)
        sound_row.addWidget(preview)
        sound_row.addStretch()
        form.addRow(i18n.get_translation("alarm_sound"), _wrap(sound_row, self))

        self._snooze_combo = QComboBox(self)
        for minutes in SNOOZE_PRESET_MINUTES:
            self._snooze_combo.addItem(duration_text(i18n, minutes), minutes)
        form.addRow(i18n.get_translation("alarm_snooze_duration"), self._snooze_combo)

        self._limit_combo = QComboBox(self)
        for limit in SNOOZE_LIMIT_PRESETS:
            text = (
                i18n.get_translation("snooze_unlimited")
                if limit is None
                else i18n.format_number(limit)
            )
            self._limit_combo.addItem(text, limit)
        form.addRow(i18n.get_translation("alarm_snooze_limit"), self._limit_combo)

        self._enabled_check = QCheckBox(i18n.get_translation("alarm_enabled"))
        form.addRow("", self._enabled_check)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._repeat_radio.toggled.connect(self._mode_changed)
        self._populate(alarm, default_time)
        self._mode_changed()

    # ------------------------------------------------------------------
    # Population and state
    # ------------------------------------------------------------------
    def _populate(
        self, alarm: Alarm | None, default_time: tuple[int, int] | None
    ) -> None:
        if alarm is None:
            self._repeat_radio.setChecked(True)
            for chip in self._day_chips:
                chip.setChecked(True)
            if default_time is not None:
                self._time_picker.set_time(*default_time)
            self._select_color(next(iter(self._color_buttons)))
            self._enabled_check.setChecked(True)
            self._select_snooze(self._snooze_combo, None)
            return
        self._label_edit.setText(alarm.label)
        self._time_picker.set_time(alarm.hour, alarm.minute)
        if alarm.is_repeating:
            self._repeat_radio.setChecked(True)
            for day in alarm.weekdays:
                self._day_chips[day].setChecked(True)
        else:
            self._one_off_radio.setChecked(True)
            when = alarm.one_off_date
            self._calendar.setSelectedDate(QDate(when.year, when.month, when.day))
        self._select_color(alarm.color)
        index = self._sound_combo.findData(alarm.sound)
        self._sound_combo.setCurrentIndex(max(0, index))
        self._select_snooze(self._snooze_combo, alarm.snooze_minutes)
        limit_index = self._limit_combo.findData(alarm.snooze_limit)
        self._limit_combo.setCurrentIndex(max(0, limit_index))
        self._enabled_check.setChecked(alarm.enabled)

    def _select_snooze(self, combo: QComboBox, minutes: int | None) -> None:
        wanted = minutes if minutes is not None else DEFAULT_SNOOZE_MINUTES
        index = combo.findData(wanted)
        combo.setCurrentIndex(max(0, index))

    def _select_color(self, name: str) -> None:
        button = self._color_buttons.get(name)
        if button is not None:
            button.setChecked(True)
        self._restyle_swatches()

    def _selected_color(self) -> str:
        for name, button in self._color_buttons.items():
            if button.isChecked():
                return name
        return next(iter(self._color_buttons))

    def _restyle_swatches(self) -> None:
        for (_name, hex_value), button in zip(
            ALARM_COLORS, self._color_buttons.values()
        ):
            button.setStyleSheet(_swatch_style(hex_value, button.isChecked()))

    def _mode_changed(self, _checked: bool = False) -> None:
        repeating = self._repeat_radio.isChecked()
        self._days_widget.setVisible(repeating)
        self._calendar.setVisible(not repeating)
        self._validate()

    def _validate(self, _checked: bool = False) -> None:
        valid = True
        if self._repeat_radio.isChecked():
            valid = any(chip.isChecked() for chip in self._day_chips)
        ok = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setEnabled(valid)

    def _change_timezone(self) -> None:
        chosen = pick_timezone(self, self._i18n, self._timezone_service)
        if chosen:
            self._tz_id = chosen
            self._tz_label.setText(chosen)

    def _preview_sound(self) -> None:
        self._sound_player.preview(self._sound_combo.currentData(), PREVIEW_VOLUME)

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------
    def result_alarm(self) -> Alarm:
        """Build the alarm from the dialog state."""
        if self._repeat_radio.isChecked():
            weekdays = tuple(
                day for day, chip in enumerate(self._day_chips) if chip.isChecked()
            )
            one_off = None
        else:
            weekdays = ()
            selected = self._calendar.selectedDate()
            one_off = date(selected.year(), selected.month(), selected.day())
        return Alarm(
            alarm_id=self._alarm_id,
            label=self._label_edit.text().strip(),
            hour=self._time_picker.hour(),
            minute=self._time_picker.minute(),
            weekdays=weekdays,
            one_off_date=one_off,
            tz_id=self._tz_id,
            color=self._selected_color(),
            sound=self._sound_combo.currentData(),
            snooze_minutes=self._snooze_combo.currentData(),
            snooze_limit=self._limit_combo.currentData(),
            enabled=self._enabled_check.isChecked(),
        )


def _wrap(layout, parent: QWidget) -> QWidget:
    """Wrap a layout in a widget for QFormLayout rows."""
    widget = QWidget(parent)
    widget.setLayout(layout)
    return widget
