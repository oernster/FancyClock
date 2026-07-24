"""Clock window skin selection and persistence mixin."""

from __future__ import annotations

from pathlib import PurePath

from PySide6.QtGui import QAction

from fancyclock.domain.skins import DEFAULT_SKIN_STEM, skin_stem


class WindowSkinMixin:
    """Adds media skin selection and persistence."""

    def _apply_startup_skin(self) -> None:
        """Apply the saved skin, defaulting to the standard skin if unset."""
        saved_name = self.settings.skin_name()
        if saved_name:
            path = self.skin_service.find_by_stem(saved_name)
            if path:
                self.analog_clock.set_video_skin(path)
                return

        default_path = self.skin_service.find_by_stem(DEFAULT_SKIN_STEM)
        if default_path:
            self.analog_clock.set_video_skin(default_path)
            self.settings.set_skin_name(DEFAULT_SKIN_STEM)

    def _set_skin_and_persist(self, path: str | None) -> None:
        """Set the current skin and persist the choice."""
        self.analog_clock.set_video_skin(path)
        if path:
            self.settings.set_skin_name(skin_stem(PurePath(path).name))
        else:
            self.settings.set_skin_name(None)

    def _populate_skins_menu(self) -> None:
        """(Re)build the Skins menu from the available skin files."""
        if not hasattr(self, "skins_menu"):
            return

        self.skins_menu.clear()

        default_label = self.i18n_manager.get_translation("skin_default")
        if default_label == "skin_default":
            default_label = "Starfield"
        default_action = QAction(default_label, self)
        default_action.triggered.connect(lambda: self._set_skin_and_persist(None))
        self.skins_menu.addAction(default_action)

        for entry in self.skin_service.entries():
            action = QAction(entry.display_name, self)
            action.triggered.connect(
                lambda checked=False, p=entry.path: self._set_skin_and_persist(p)
            )
            self.skins_menu.addAction(action)
