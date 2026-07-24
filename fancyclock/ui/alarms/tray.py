"""System tray icon with the alarm quick menu."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget


class AlarmTray(QObject):
    """Wraps QSystemTrayIcon: menu, tooltip and notifications."""

    show_requested = Signal()
    manager_requested = Signal()
    master_toggled = Signal(bool)
    quit_requested = Signal()

    def __init__(
        self,
        i18n,
        icon: QIcon,
        master_enabled: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._tray = QSystemTrayIcon(icon, self)

        menu = QMenu()
        self._menu = menu

        show_action = QAction(i18n.get_translation("tray_show"), menu)
        show_action.triggered.connect(self.show_requested.emit)
        menu.addAction(show_action)

        manage_action = QAction(i18n.get_translation("alarms_manage"), menu)
        manage_action.triggered.connect(self.manager_requested.emit)
        menu.addAction(manage_action)

        menu.addSeparator()

        self._next_action = QAction("", menu)
        self._next_action.setEnabled(False)
        menu.addAction(self._next_action)

        self._master_action = QAction(
            i18n.get_translation("alarms_enabled_master"), menu
        )
        self._master_action.setCheckable(True)
        self._master_action.setChecked(master_enabled)
        self._master_action.toggled.connect(self.master_toggled.emit)
        menu.addAction(self._master_action)

        menu.addSeparator()

        quit_action = QAction(i18n.get_translation("tray_quit"), menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._activated)
        self._tray.show()

    @staticmethod
    def available() -> bool:
        """Return whether the platform offers a system tray."""
        return QSystemTrayIcon.isSystemTrayAvailable()

    def _activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_requested.emit()

    def set_master(self, enabled: bool) -> None:
        """Reflect the master switch without re-emitting."""
        self._master_action.blockSignals(True)
        self._master_action.setChecked(enabled)
        self._master_action.blockSignals(False)

    def set_next_text(self, text: str) -> None:
        """Update the next-alarm line and tooltip."""
        self._next_action.setText(text)
        self._tray.setToolTip(text)

    def notify(self, title: str, text: str) -> None:
        """Show a best-effort system notification."""
        self._tray.showMessage(title, text)

    def hide(self) -> None:
        """Remove the tray icon."""
        self._tray.hide()
