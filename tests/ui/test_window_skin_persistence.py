"""The chosen skin survives a restart, Starfield included.

Each test builds the real ClockWindow over a real JSON settings file in a temp
directory and the shipped media folder, picks a skin through the real Skins
menu, then builds a second window from the same settings file, which is what
the next start of the app does. Only the reference time source is replaced,
so the tests never reach the network.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fancyclock.application.localization import LocalizationService
from fancyclock.application.resources import ResourcePaths
from fancyclock.application.settings import SKIN_NAME_KEY, SettingsService
from fancyclock.application.skins import SkinService
from fancyclock.application.time_service import TimeService
from fancyclock.application.timezones import TimezoneService
from fancyclock.domain.skins import DEFAULT_SKIN_STEM, STARFIELD_SKIN_NAME
from fancyclock.infrastructure.clock import SystemClock
from fancyclock.infrastructure.json_settings_store import (
    SETTINGS_FILE_NAME,
    JsonSettingsStore,
)
from fancyclock.infrastructure.media_library import FilesystemMediaLibrary
from fancyclock.infrastructure.resources import (
    MEDIA_RELATIVE_DIR,
    TIMEZONE_MAP_FILENAME,
    TRANSLATIONS_RELATIVE_DIR,
    find_license_file,
    get_about_icon_path,
    get_app_icon_path,
    get_sounds_dir_path,
    resource_path,
)
from fancyclock.infrastructure.system_locale_probe import EnvironmentLocaleProbe
from fancyclock.infrastructure.timezone_catalog import PytzTimezoneCatalog
from fancyclock.infrastructure.timezone_locale_map import JsonTimezoneLocaleMap
from fancyclock.infrastructure.translations_repo import JsonTranslationsRepository
from fancyclock.ui.window import ClockWindow

STARFIELD_MENU_INDEX = 0
OTHER_SKIN_STEM = "waves"


class OfflineTimeSource:
    """A reference clock that answers without touching the network."""

    def utc_time(self) -> datetime:
        return datetime.now(timezone.utc)


def _build_window(config_dir: Path) -> ClockWindow:
    """Build the window as the composition root does, over ``config_dir``."""
    i18n = LocalizationService(
        translations=JsonTranslationsRepository(
            Path(resource_path(TRANSLATIONS_RELATIVE_DIR))
        ),
        tz_locale_map=JsonTimezoneLocaleMap(Path(resource_path(TIMEZONE_MAP_FILENAME))),
        system_probe=EnvironmentLocaleProbe(),
    )
    return ClockWindow(
        i18n_manager=i18n,
        time_service=TimeService(source=OfflineTimeSource(), clock=SystemClock()),
        settings=SettingsService(store=JsonSettingsStore(config_dir)),
        skin_service=SkinService(
            media=FilesystemMediaLibrary(Path(resource_path(MEDIA_RELATIVE_DIR)))
        ),
        timezone_service=TimezoneService(catalog=PytzTimezoneCatalog()),
        resources=ResourcePaths(
            app_icon=get_app_icon_path(),
            about_icon_png=get_about_icon_path(),
            license_file=find_license_file(),
            sounds_dir=get_sounds_dir_path(),
        ),
    )


def _current_skin(window: ClockWindow) -> str | None:
    return window.analog_clock._current_skin


def _menu_action_for_stem(window: ClockWindow, stem: str):
    path = window.skin_service.find_by_stem(stem)
    for action in window.skins_menu.actions():
        if window._skin_label(_entry_for(window, path)) == action.text():
            return action
    raise AssertionError(f"no Skins menu entry for {stem}")


def _entry_for(window: ClockWindow, path: str):
    return next(e for e in window.skin_service.entries() if e.path == path)


def test_first_start_uses_the_default_skin(qapp, tmp_path) -> None:
    window = _build_window(tmp_path)

    expected = window.skin_service.find_by_stem(DEFAULT_SKIN_STEM)
    assert _current_skin(window) == expected


def test_starfield_choice_survives_a_restart(qapp, tmp_path) -> None:
    first = _build_window(tmp_path)
    first.skins_menu.actions()[STARFIELD_MENU_INDEX].trigger()
    assert _current_skin(first) is None
    first.close()

    second = _build_window(tmp_path)

    saved = json.loads((tmp_path / SETTINGS_FILE_NAME).read_text("utf-8"))
    assert _current_skin(second) is None, (
        f"Starfield was chosen but the next start showed {_current_skin(second)}; "
        f"saved settings: {saved}"
    )


def test_video_skin_choice_survives_a_restart(qapp, tmp_path) -> None:
    first = _build_window(tmp_path)
    _menu_action_for_stem(first, OTHER_SKIN_STEM).trigger()
    first.close()

    second = _build_window(tmp_path)

    assert _current_skin(second) == second.skin_service.find_by_stem(OTHER_SKIN_STEM)


def test_no_shipped_video_takes_the_starfield_name(qapp, tmp_path) -> None:
    """A video named like the marker would come back as Starfield."""
    window = _build_window(tmp_path)

    assert window.skin_service.find_by_stem(STARFIELD_SKIN_NAME) is None


def test_skin_saved_by_an_older_version_still_loads(qapp, tmp_path) -> None:
    (tmp_path / SETTINGS_FILE_NAME).write_text(
        json.dumps({SKIN_NAME_KEY: OTHER_SKIN_STEM}), encoding="utf-8"
    )

    window = _build_window(tmp_path)

    assert _current_skin(window) == window.skin_service.find_by_stem(OTHER_SKIN_STEM)
