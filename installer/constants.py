"""Installer constants.

Keep Windows paths/registry constants in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fancyclock.version import APP_AUTHOR, APP_DISPLAY_NAME

UNINSTALL_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FancyClock"


@dataclass(frozen=True, slots=True)
class InstallerIdentity:
    app_name: str = APP_DISPLAY_NAME
    publisher: str = APP_AUTHOR

    uninstall_key: str = UNINSTALL_REG_KEY
    uninstall_key_name: str = "FancyClock"

    # Location under the install root where we copy the installer exe so it can
    # act as the registered uninstaller.
    installer_subdir: str = "_installer"
    installer_exe_name: str = "FancyClockSetup.exe"

    # Start menu folder name under the per-user Programs directory.
    start_menu_folder: str = "FancyClock"
    shortcut_name: str = "Fancy Clock"

    def installer_exe_path(self, install_root: Path) -> Path:
        return install_root / self.installer_subdir / self.installer_exe_name
