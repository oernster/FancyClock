"""Clock window menu/dialog behavior mixin."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QSizePolicy, QWidget

from dialogs import AboutDialog, LicenseDialog, show_timezone_dialog


class WindowMenuMixin:
    """Adds menu bar creation and help dialogs."""

    def _create_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        menu_bar.addMenu("").addAction(QAction("", self))
        menu_bar.setCornerWidget(spacer)

        self.timezone_action = QAction(
            self.i18n_manager.get_translation("timezone"), self
        )
        self.timezone_action.triggered.connect(lambda: show_timezone_dialog(self))
        menu_bar.addAction(self.timezone_action)

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

    def show_about_dialog(self) -> None:
        if not hasattr(self, "about_dialog") or self.about_dialog is None:
            self.about_dialog = AboutDialog(self.i18n_manager, self)
        self.about_dialog.refresh_text()
        self.about_dialog.show()
        self.about_dialog.raise_()
        self.about_dialog.activateWindow()

    def show_license_dialog(self) -> None:
        if not hasattr(self, "license_dialog") or self.license_dialog is None:
            self.license_dialog = LicenseDialog(self.i18n_manager, self)
        self.license_dialog.refresh_text()
        self.license_dialog.show()
        self.license_dialog.raise_()
        self.license_dialog.activateWindow()
