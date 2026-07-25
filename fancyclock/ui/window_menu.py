"""Clock window menu/dialog behavior mixin."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QSizePolicy, QWidget

from fancyclock.ui.dialogs import (
    AboutDialog,
    LicenseDialog,
    show_timezone_dialog,
)


class WindowMenuMixin:
    """Adds menu bar creation and help dialogs."""

    def _create_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        # Render the menu inside the window on every platform. macOS otherwise
        # uses the native global menu bar, which drops the bare Timezone action
        # (only submenus survive there), hiding the internationalisation entry.
        menu_bar.setNativeMenuBar(False)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        menu_bar.addMenu("").addAction(QAction("", self))
        menu_bar.setCornerWidget(spacer)

        self.timezone_action = QAction(
            self.i18n_manager.get_translation("timezone"), self
        )
        self.timezone_action.triggered.connect(
            lambda: show_timezone_dialog(self, self.timezone_service)
        )
        menu_bar.addAction(self.timezone_action)

        if self.alarms_controller is not None:
            self._create_alarms_menu(menu_bar)

        if self._opacity_supported:
            self._create_view_menu(menu_bar)

        skins_label = self.i18n_manager.get_translation("skins")
        if skins_label == "skins":
            skins_label = "Skins"
        self.skins_menu = menu_bar.addMenu(skins_label)
        self._populate_skins_menu()

        self.help_menu = menu_bar.addMenu(self.i18n_manager.get_translation("help"))
        self.about_action = QAction(self.i18n_manager.get_translation("about"), self)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.help_menu.addAction(self.about_action)

        self.license_action = QAction(
            self.i18n_manager.get_translation("license"), self
        )
        self.license_action.triggered.connect(self.show_license_dialog)
        self.help_menu.addAction(self.license_action)

    def _create_alarms_menu(self, menu_bar) -> None:
        """Build the Alarms menu backed by the alarms controller."""
        controller = self.alarms_controller
        i18n = self.i18n_manager
        self.alarms_menu = menu_bar.addMenu(i18n.get_translation("alarms"))

        self.manage_alarms_action = QAction(i18n.get_translation("alarms_manage"), self)
        self.manage_alarms_action.triggered.connect(controller.open_manager)
        self.alarms_menu.addAction(self.manage_alarms_action)

        self.alarms_menu.addSeparator()

        self.master_alarms_action = QAction(
            i18n.get_translation("alarms_enabled_master"), self
        )
        self.master_alarms_action.setCheckable(True)
        self.master_alarms_action.toggled.connect(controller.set_master)
        self.alarms_menu.addAction(self.master_alarms_action)

        self.close_to_tray_action = QAction(i18n.get_translation("close_to_tray"), self)
        self.close_to_tray_action.setCheckable(True)
        self.close_to_tray_action.toggled.connect(controller.set_close_to_tray)
        self.alarms_menu.addAction(self.close_to_tray_action)

        self.autostart_action = None
        if controller.autostart_supported():
            self.autostart_action = QAction(
                i18n.get_translation("start_on_login"), self
            )
            self.autostart_action.setCheckable(True)
            self.autostart_action.toggled.connect(controller.set_autostart)
            self.alarms_menu.addAction(self.autostart_action)

        self.alarms_menu.aboutToShow.connect(self._sync_alarms_menu)

    def _sync_alarms_menu(self) -> None:
        """Reflect live state in the Alarms menu check marks."""
        controller = self.alarms_controller
        pairs = [
            (self.master_alarms_action, controller.master_enabled()),
            (self.close_to_tray_action, controller.close_to_tray_enabled()),
        ]
        if self.autostart_action is not None:
            pairs.append((self.autostart_action, controller.autostart_enabled()))
        for action, value in pairs:
            action.blockSignals(True)
            action.setChecked(value)
            action.blockSignals(False)

    def show_about_dialog(self) -> None:
        if not hasattr(self, "about_dialog") or self.about_dialog is None:
            self.about_dialog = AboutDialog(self.i18n_manager, self.resources, self)
        self.about_dialog.refresh_text()
        self.about_dialog.show()
        self.about_dialog.raise_()
        self.about_dialog.activateWindow()

    def show_license_dialog(self) -> None:
        if not hasattr(self, "license_dialog") or self.license_dialog is None:
            self.license_dialog = LicenseDialog(
                self.i18n_manager, self.resources.license_file, self
            )
        self.license_dialog.refresh_text()
        self.license_dialog.show()
        self.license_dialog.raise_()
        self.license_dialog.activateWindow()
