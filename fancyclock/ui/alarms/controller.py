"""The alarms UI controller: ticks, ringing, tray, toggles and dialogs."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from fancyclock.domain.alarms import DEFAULT_COLOR, color_hex
from fancyclock.ui.alarms.firing_window import AlarmFiringWindow
from fancyclock.ui.alarms.formatting import occurrence_text, time_text
from fancyclock.ui.alarms.manager_dialog import AlarmManagerDialog
from fancyclock.ui.alarms.missed_dialog import show_missed_dialog
from fancyclock.ui.alarms.sound import AlarmSoundPlayer
from fancyclock.ui.alarms.toast import Toast
from fancyclock.ui.alarms.tray import AlarmTray

MAX_RING_MS = 10 * 60 * 1000


class AlarmsUiController(QObject):
    """Owns every alarm-facing UI element and reacts to service ticks."""

    def __init__(
        self,
        window,
        alarm_service,
        settings,
        autostart,
        i18n,
        timezone_service,
        resources,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._service = alarm_service
        self._settings = settings
        self._autostart = autostart
        self._i18n = i18n
        self._timezone_service = timezone_service
        self._resources = resources

        self._sound = AlarmSoundPlayer(resources.sounds_dir, self)
        self._toast = Toast()
        self._tray: AlarmTray | None = None
        self._firing: dict[str, AlarmFiringWindow] = {}
        self._manager: AlarmManagerDialog | None = None
        self._tray_notice_shown = False
        self._last_next_text = ""

        self._ring_stop_timer = QTimer(self)
        self._ring_stop_timer.setSingleShot(True)
        self._ring_stop_timer.setInterval(MAX_RING_MS)
        self._ring_stop_timer.timeout.connect(self._sound.stop)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Create the tray (when available) and prime the tooltip."""
        if AlarmTray.available():
            self._tray = AlarmTray(
                self._i18n,
                QIcon(self._resources.app_icon),
                self._service.master_enabled(),
                parent=None,
            )
            self._tray.show_requested.connect(self._window.bring_to_front)
            self._tray.manager_requested.connect(self.open_manager)
            self._tray.master_toggled.connect(self._set_master)
            self._tray.quit_requested.connect(self.quit_app)
        self._refresh_next_summary()

    def tray_available(self) -> bool:
        """Return whether a tray icon is active."""
        return self._tray is not None

    def autostart_supported(self) -> bool:
        """Return whether the start-on-sign-in toggle should be offered."""
        return self._autostart.is_supported()

    def autostart_enabled(self) -> bool:
        """Return the current start-on-sign-in state."""
        return self._autostart.is_enabled()

    def set_autostart(self, enabled: bool) -> None:
        """Enable or disable start-on-sign-in."""
        if enabled:
            self._autostart.enable()
        else:
            self._autostart.disable()

    def close_to_tray_enabled(self) -> bool:
        """Return the close-to-tray preference."""
        return self._settings.close_to_tray()

    def set_close_to_tray(self, enabled: bool) -> None:
        """Persist the close-to-tray preference."""
        self._settings.set_close_to_tray(enabled)

    def master_enabled(self) -> bool:
        """Return the master switch state."""
        return self._service.master_enabled()

    def _set_master(self, enabled: bool) -> None:
        self._service.set_master_enabled(enabled)
        if self._tray is not None:
            self._tray.set_master(enabled)
        self._refresh_next_summary()

    def set_master(self, enabled: bool) -> None:
        """Menu hook for the master switch."""
        self._set_master(enabled)

    # ------------------------------------------------------------------
    # Ticking and ringing
    # ------------------------------------------------------------------
    def tick(self) -> None:
        """Run one service tick and surface the results."""
        result = self._service.tick()
        for ringing in result.ringing:
            self._on_ring(ringing)
        if result.missed:
            show_missed_dialog(self._window, self._i18n, result.missed)
        self._refresh_next_summary()

    def _on_ring(self, ringing) -> None:
        alarm = ringing.alarm
        existing = self._firing.get(alarm.alarm_id)
        if existing is not None:
            existing.raise_()
            existing.activateWindow()
            return

        window = AlarmFiringWindow(
            self._i18n,
            ringing,
            self._service.effective_snooze_minutes(alarm.alarm_id),
            self._service.snoozes_remaining(alarm.alarm_id),
            parent=None,
        )
        window.snoozed.connect(self._on_snoozed)
        window.dismissed.connect(self._on_dismissed)
        self._firing[alarm.alarm_id] = window
        window.show()
        window.raise_()
        window.activateWindow()

        if self._tray is not None:
            self._tray.notify(
                self._i18n.get_translation("alarm_ringing_title"),
                alarm.label or time_text(self._i18n, alarm.hour, alarm.minute),
            )
        self._sound.play_looping(alarm.sound, self._settings.alarm_volume())
        self._ring_stop_timer.start()

    def _on_snoozed(self, alarm_id: str, minutes: int) -> None:
        self._service.snooze(alarm_id, minutes)
        self._episode_ended(alarm_id)

    def _on_dismissed(self, alarm_id: str) -> None:
        self._service.dismiss(alarm_id)
        self._episode_ended(alarm_id)

    def _episode_ended(self, alarm_id: str) -> None:
        self._firing.pop(alarm_id, None)
        if not self._firing:
            self._sound.stop()
            self._ring_stop_timer.stop()
        self._refresh_next_summary()

    # ------------------------------------------------------------------
    # Summary and dialogs
    # ------------------------------------------------------------------
    def _refresh_next_summary(self) -> None:
        info = self._service.next_alarm()
        if info is None:
            text = self._i18n.get_translation("alarm_none")
        else:
            prefix = self._i18n.get_translation("alarm_next")
            when = occurrence_text(
                self._i18n,
                info.occurrence_utc,
                info.occurrence_utc.astimezone().tzinfo,
            )
            label = info.alarm.label or "-"
            text = f"{prefix}: {when} {label}"
        if text != self._last_next_text:
            self._last_next_text = text
            if self._tray is not None:
                self._tray.set_next_text(text)

    def open_manager(self) -> None:
        """Open (or focus) the alarms manager dialog."""
        if self._manager is not None and self._manager.isVisible():
            self._manager.raise_()
            self._manager.activateWindow()
            return
        self._manager = AlarmManagerDialog(
            self._i18n,
            self._service,
            self._settings,
            self._timezone_service,
            self._sound,
            default_tz_id=self._default_tz_id(),
            parent=self._window,
        )
        self._manager.exec()
        self._refresh_next_summary()

    def _default_tz_id(self) -> str:
        saved = self._settings.timezone_id()
        if saved:
            return saved
        return bytes(self._window.time_zone.id()).decode("utf-8")

    # ------------------------------------------------------------------
    # Close-to-tray and quitting
    # ------------------------------------------------------------------
    def handle_close(self, event) -> None:
        """Hide to the tray instead of quitting when configured."""
        if self.close_to_tray_enabled() and self._tray is not None:
            event.ignore()
            self._window.hide()
            if not self._tray_notice_shown:
                self._tray_notice_shown = True
                self._toast.show_message(
                    self._i18n.get_translation("tray_still_running"),
                    color_hex(DEFAULT_COLOR),
                )
            return
        event.accept()

    def quit_app(self) -> None:
        """Quit the application from the tray menu."""
        self._sound.stop()
        if self._tray is not None:
            self._tray.hide()
        QApplication.instance().quit()
