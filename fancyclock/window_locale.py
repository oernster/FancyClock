"""Clock window locale/timezone behavior mixin."""

from __future__ import annotations

from PySide6.QtCore import QTimeZone

from settings_store import get_setting, set_setting


class WindowLocaleMixin:
    """Adds locale/timezone helpers and persistence."""

    def _get_locale_for_timezone(self, tz_id: str) -> str:
        """Return the most appropriate locale for a given timezone."""
        try:
            return (
                self.i18n_manager.locale_detector.get_locale_from_timezone(tz_id)
                or "en_US"
            )
        except Exception:
            return "en_US"

    def _change_timezone(self, tz_id: str) -> None:
        """Update timezone, locale, persist both, and retranslate the UI."""
        try:
            self.time_zone = QTimeZone(tz_id.encode("utf-8"))
        except Exception:
            return

        try:
            set_setting("timezone_id", tz_id)
        except Exception:
            pass

        locale = self._get_locale_for_timezone(tz_id)
        try:
            if locale:
                self.i18n_manager.set_locale(locale)
                set_setting("locale", self.i18n_manager.current_locale)
        except Exception:
            pass

        try:
            self.retranslate_ui()
            self.update_time()
        except Exception:
            pass

        try:
            if hasattr(self, "about_dialog") and self.about_dialog.isVisible():
                self.about_dialog.refresh_text()
        except Exception:
            pass

    def _restore_locale_and_timezone(self) -> None:
        """Restore saved locale and timezone from JSON settings."""
        saved_tz = get_setting("timezone_id", None)
        saved_locale = get_setting("locale", None)

        if isinstance(saved_tz, str) and saved_tz:
            try:
                self._change_timezone(saved_tz)
            except Exception:
                pass

        if isinstance(saved_locale, str) and saved_locale:
            try:
                self.i18n_manager.set_locale(saved_locale)
                self.retranslate_ui()
                self.update_time()
            except Exception:
                pass

    def retranslate_ui(self) -> None:
        """Update UI text strings to the current locale."""
        try:
            self.setWindowTitle(self.i18n_manager.get_translation("app_name"))
        except Exception:
            pass

        try:
            self.timezone_action.setText(self.i18n_manager.get_translation("timezone"))
        except Exception:
            pass

        try:
            self.help_menu.setTitle(self.i18n_manager.get_translation("help"))
            self.about_action.setText(self.i18n_manager.get_translation("about"))
            self.license_action.setText(self.i18n_manager.get_translation("license"))
        except Exception:
            pass

        try:
            skins_label = self.i18n_manager.get_translation("skins")
            if skins_label == "skins":
                skins_label = "Skins"
            self.skins_menu.setTitle(skins_label)
            self._populate_skins_menu()
        except Exception:
            pass

        try:
            if hasattr(self, "about_dialog") and self.about_dialog.isVisible():
                self.about_dialog.refresh_text()
        except Exception:
            pass

        try:
            if hasattr(self, "license_dialog") and self.license_dialog.isVisible():
                self.license_dialog.refresh_text()
        except Exception:
            pass
