"""Clock window locale/timezone behavior mixin.

Retranslating the window is a sequence of independent steps: the title, each
menu, the alarms controller, any open dialog. One of them failing must not
stop the others. A single missing widget would otherwise leave the rest of the
window in the previous language with nothing said about it.

That intent used to be written out once per step as its own try/except, which
is why this file held sixteen broad handlers. It is now stated once, in
``_run_independently``, with each step a named method the sequence lists. The
behaviour is identical: every step still runs, a failing one still costs only
itself.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimeZone

# Menu label to fall back to when the translation is missing entirely and the
# resolver hands back the key itself.
_SKINS_KEY = "skins"
_SKINS_FALLBACK = "Skins"


def _run_independently(step: Callable[[], None]) -> None:
    """Run one window-update step, letting a failure cost only that step.

    Every caller is a piece of Qt text setting that the window would rather
    skip than crash on: a widget the current layout does not have, a dialog
    closed between the check and the call, a translation the locale lacks.
    None of it is worth refusing to change language over; none of it is
    recoverable here beyond leaving that one piece as it was.
    """
    try:
        step()
    except Exception:  # noqa: BLE001
        # Deliberate: see the docstring above. The alternative is a window
        # stuck in the old language because one menu could not be relabelled.
        pass


class WindowLocaleMixin:
    """Adds locale/timezone helpers and persistence."""

    def _change_timezone(self, tz_id: str) -> None:
        """Update timezone, locale, persist both and retranslate the UI."""
        try:
            self.time_zone = QTimeZone(tz_id.encode("utf-8"))
        except (UnicodeError, ValueError, TypeError):
            # A zone id that is not encodable or not a string is the one
            # failure worth abandoning the change for: there is no timezone to
            # move to, so persisting or retranslating would record a lie.
            return

        for step in (
            lambda: self.settings.set_timezone_id(tz_id),
            lambda: self._apply_locale_for_timezone(tz_id),
            self._refresh_time_display,
            self._refresh_open_about_dialog,
        ):
            _run_independently(step)

    def _apply_locale_for_timezone(self, tz_id: str) -> None:
        """Move to the locale this timezone implies and persist it."""
        locale = self.i18n_manager.locale_for_timezone_or_fallback(tz_id)
        if self.i18n_manager.set_locale(locale):
            self.settings.set_locale(self.i18n_manager.current_locale)

    def _refresh_time_display(self) -> None:
        """Relabel the window then redraw the clock in the new language."""
        self.retranslate_ui()
        self.update_time()

    def _restore_locale_and_timezone(self) -> None:
        """Restore saved locale and timezone from settings."""
        saved_tz = self.settings.timezone_id()
        saved_locale = self.settings.locale()

        if saved_tz:
            _run_independently(lambda: self._change_timezone(saved_tz))

        if saved_locale:
            _run_independently(lambda: self._apply_saved_locale(saved_locale))

    def _apply_saved_locale(self, locale: str) -> None:
        """Move to a locale read back from settings and relabel the window."""
        self.i18n_manager.set_locale(locale)
        self._refresh_time_display()

    def retranslate_ui(self) -> None:
        """Update UI text strings to the current locale.

        Each step is independent, so the sequence continues past one that
        fails. See ``_run_independently`` for why that is the right trade here.
        """
        for step in (
            self._retranslate_window_title,
            self._retranslate_timezone_action,
            self._retranslate_help_menu,
            self._retranslate_skins_menu,
            self._retranslate_alarms_menu,
            self._retranslate_view_menu,
            self._retranslate_alarms_controller,
            self._refresh_open_about_dialog,
            self._refresh_open_licence_dialog,
        ):
            _run_independently(step)

    def _retranslate_window_title(self) -> None:
        self.setWindowTitle(self.i18n_manager.get_translation("app_name"))

    def _retranslate_timezone_action(self) -> None:
        self.timezone_action.setText(self.i18n_manager.get_translation("timezone"))

    def _retranslate_help_menu(self) -> None:
        self.help_menu.setTitle(self.i18n_manager.get_translation("help"))
        self.about_action.setText(self.i18n_manager.get_translation("about"))
        self.license_action.setText(self.i18n_manager.get_translation("license"))

    def _retranslate_skins_menu(self) -> None:
        label = self.i18n_manager.get_translation(_SKINS_KEY)
        if label == _SKINS_KEY:
            label = _SKINS_FALLBACK
        self.skins_menu.setTitle(label)
        self._populate_skins_menu()

    def _retranslate_alarms_controller(self) -> None:
        if self.alarms_controller is not None:
            self.alarms_controller.retranslate()

    def _refresh_open_about_dialog(self) -> None:
        if hasattr(self, "about_dialog") and self.about_dialog.isVisible():
            self.about_dialog.refresh_text()

    def _refresh_open_licence_dialog(self) -> None:
        if hasattr(self, "license_dialog") and self.license_dialog.isVisible():
            self.license_dialog.refresh_text()
