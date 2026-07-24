"""Application entrypoint and composition root.

This is the only module allowed to import the infrastructure layer: it
builds every infrastructure implementation, injects it into the application
services and hands those to the UI.
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLoggingCategory
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from fancyclock.application.localization import LocalizationService
from fancyclock.application.resources import ResourcePaths
from fancyclock.application.settings import SettingsService
from fancyclock.application.skins import SkinService
from fancyclock.application.time_service import TimeService
from fancyclock.application.timezones import TimezoneService
from fancyclock.infrastructure.clock import SystemClock
from fancyclock.infrastructure.json_settings_store import JsonSettingsStore
from fancyclock.infrastructure.media_library import FilesystemMediaLibrary
from fancyclock.infrastructure.ntp_time_source import NtpTimeSource
from fancyclock.infrastructure.resources import (
    find_license_file,
    get_about_icon_path,
    get_app_icon_path,
    resource_path,
)
from fancyclock.infrastructure.single_instance import SingleInstanceGuard
from fancyclock.infrastructure.system_locale_probe import EnvironmentLocaleProbe
from fancyclock.infrastructure.timezone_catalog import PytzTimezoneCatalog
from fancyclock.infrastructure.timezone_locale_map import JsonTimezoneLocaleMap
from fancyclock.infrastructure.translations_repo import JsonTranslationsRepository
from fancyclock.ui.window import ClockWindow

APP_ID = "uk.codecrafter.FancyClock"
SINGLETON_NAME = "uk.codecrafter.FancyClock.singleton"
ORGANIZATION_NAME = "OliverErnster"
APPLICATION_NAME = "FancyClock"
TRANSLATIONS_RELATIVE_DIR = "localization/translations"
TIMEZONE_MAP_FILENAME = "timezone_locale_map.json"
MEDIA_RELATIVE_DIR = "media"
LOG_FILTER_RULES = (
    "qt.text.font.db=false\n"
    "qt.multimedia.ffmpeg=false\n"
    "qt.multimedia.ffmpeg.*=false\n"
)


def _build_window() -> ClockWindow:
    """Wire infrastructure into application services and build the window."""
    i18n_manager = LocalizationService(
        translations=JsonTranslationsRepository(
            Path(resource_path(TRANSLATIONS_RELATIVE_DIR))
        ),
        tz_locale_map=JsonTimezoneLocaleMap(Path(resource_path(TIMEZONE_MAP_FILENAME))),
        system_probe=EnvironmentLocaleProbe(),
    )
    time_service = TimeService(source=NtpTimeSource(), clock=SystemClock())
    settings = SettingsService(store=JsonSettingsStore())
    skin_service = SkinService(
        media=FilesystemMediaLibrary(Path(resource_path(MEDIA_RELATIVE_DIR)))
    )
    timezone_service = TimezoneService(catalog=PytzTimezoneCatalog())
    resources = ResourcePaths(
        app_icon=get_app_icon_path(),
        about_icon_png=get_about_icon_path(),
        license_file=find_license_file(),
    )
    return ClockWindow(
        i18n_manager=i18n_manager,
        time_service=time_service,
        settings=settings,
        skin_service=skin_service,
        timezone_service=timezone_service,
        resources=resources,
    )


def main() -> int:
    """Run the FancyClock Qt application."""
    QLoggingCategory.setFilterRules(LOG_FILTER_RULES)

    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass

    QGuiApplication.setDesktopFileName(APP_ID)
    app = QApplication(sys.argv)

    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(APPLICATION_NAME)

    guard = SingleInstanceGuard(SINGLETON_NAME)
    if not guard.acquire():
        guard.notify_existing_instance()
        return 0

    app.single_instance_guard = guard

    window = _build_window()
    guard.activated.connect(window.bring_to_front)

    window.show()
    return app.exec()
