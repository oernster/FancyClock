"""Clock window skin/menu behavior mixin."""

from __future__ import annotations

import os

from PySide6.QtGui import QAction

from settings_store import get_setting, set_setting
from utils import resource_path


class WindowSkinMixin:
    """Adds media skin selection and persistence."""

    def _find_skin_by_name(self, name: str) -> str | None:
        """Search media/ for an mp4 whose stem matches the given name."""
        media_dir = resource_path("media")
        if not os.path.isdir(media_dir):
            return None

        name = name.lower()
        for filename in os.listdir(media_dir):
            if not filename.lower().endswith(".mp4"):
                continue
            stem, _ = os.path.splitext(filename)
            if stem.lower() == name:
                return os.path.join(media_dir, filename)
        return None

    def _apply_startup_skin(self) -> None:
        """Apply saved skin if present.

        If no saved skin is present, default to 'Mesmerize' if available.
        """
        saved_name = get_setting("skin_name", None)
        if isinstance(saved_name, str):
            path = self._find_skin_by_name(saved_name)
            if path:
                self.analog_clock.set_video_skin(path)
                return

        mesmerize = self._find_skin_by_name("mesmerize")
        if mesmerize:
            self.analog_clock.set_video_skin(mesmerize)
            set_setting("skin_name", "mesmerize")

    def _set_skin_and_persist(self, path: str | None) -> None:
        """Set the current skin and persist it in JSON settings."""
        self.analog_clock.set_video_skin(path)
        if path:
            stem, _ = os.path.splitext(os.path.basename(path))
            set_setting("skin_name", stem)
        else:
            set_setting("skin_name", None)

    def _populate_skins_menu(self) -> None:
        """(Re)build the Skins menu from media/*.mp4 files."""
        if not hasattr(self, "skins_menu"):
            return

        self.skins_menu.clear()

        default_label = self.i18n_manager.get_translation("skin_default")
        if default_label == "skin_default":
            default_label = "Starfield"
        default_action = QAction(default_label, self)
        default_action.triggered.connect(lambda: self._set_skin_and_persist(None))
        self.skins_menu.addAction(default_action)

        media_dir = resource_path("media")
        if not os.path.isdir(media_dir):
            return

        for filename in sorted(os.listdir(media_dir)):
            if not filename.lower().endswith(".mp4"):
                continue
            path = os.path.join(media_dir, filename)
            nice_name = os.path.splitext(filename)[0].replace("_", " ").title()
            action = QAction(nice_name, self)
            action.triggered.connect(
                lambda checked=False, p=path: self._set_skin_and_persist(p)
            )
            self.skins_menu.addAction(action)
