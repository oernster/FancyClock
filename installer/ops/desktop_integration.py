"""Registering an installed bundle with Windows.

Everything that makes a directory of files behave like an installed
application: the Apps and Features entry, the icon assets shortcuts point at,
the start-on-sign-in value and the shortcuts themselves.

This is a separate concern from `install_ops`, which is about getting the files
into place correctly and rolling back when it cannot. Every function here runs
after the bundle is already on disk, and none of them can leave a half-written
installation behind: the worst outcome is a working application with a missing
shortcut or a stale icon.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from fancyclock.version import APP_AUTHOR, APP_DISPLAY_NAME, __version__
from installer.constants import InstallerIdentity
from installer.ops.shortcuts import create_shortcut, get_shortcut_paths
from installer.shared.resource_path import resource_path
from installer.state.registry import (
    clear_run_at_signin,
    set_run_at_signin,
    write_uninstall_entry,
)

logger = logging.getLogger("installer.install")

APP_EXE_NAME = "FancyClock.exe"
DEPLOYED_ICO_NAME = "fancyclock.ico"
DEPLOYED_PNG_NAMES = (
    "fancyclock_icon_16.png",
    "fancyclock_icon_32.png",
    "fancyclock_icon_48.png",
    "fancyclock_icon_64.png",
    "fancyclock_icon_128.png",
    "fancyclock_icon_256.png",
    "fancyclock_icon_512.png",
)


def register_uninstall(
    identity: InstallerIdentity,
    *,
    install_dir: Path,
    installer_copy: Path,
    shortcut_desktop: bool,
    shortcut_start_menu: bool,
    start_on_signin: bool,
) -> None:
    """Write the Apps and Features entry for this installation."""
    exe = install_dir / APP_EXE_NAME
    uninstall_cmd = f'"{installer_copy}" --uninstall'

    # Use multi-resolution ICO if available.
    display_icon = str(exe)
    ico_path = install_dir / DEPLOYED_ICO_NAME
    if ico_path.exists():
        display_icon = str(ico_path)

    write_uninstall_entry(
        identity.uninstall_key,
        display_name=APP_DISPLAY_NAME,
        display_version=__version__,
        install_location=install_dir,
        uninstall_string=uninstall_cmd,
        display_icon=display_icon,
        publisher=APP_AUTHOR,
        shortcut_desktop=shortcut_desktop,
        shortcut_start_menu=shortcut_start_menu,
        start_on_signin=start_on_signin,
        installer_path=str(installer_copy),
    )


def deploy_runtime_icon_assets(*, install_dir: Path) -> None:
    """Deploy icon assets next to FancyClock.exe.

    - ICO (multi-resolution): for shortcuts via shell API
    - PNGs: for Qt runtime fallback if ICO unavailable
    """

    # The installer bundles the icon files at its data root via --add-data.
    ico = resource_path(DEPLOYED_ICO_NAME)
    if ico.exists():
        try:
            shutil.copy2(ico, install_dir / DEPLOYED_ICO_NAME)
        except OSError:
            # Icon assets are cosmetic. Failing to place one degrades to Qt's
            # default icon rather than a failed installation.
            pass

    for name in DEPLOYED_PNG_NAMES:
        src = resource_path(name)
        if not src.exists():
            continue
        try:
            shutil.copy2(src, install_dir / name)
        except OSError:
            # As above: a missing PNG size costs appearance, not function.
            continue


def apply_autostart(install_dir: Path, enable: bool) -> None:
    """Write or remove the per-user Run value for start-on-sign-in.

    The value name matches the one the app's own Alarms menu toggle
    manages, so the installer and the app never disagree.
    """
    exe = install_dir / APP_EXE_NAME
    logger.info("Applying start-on-sign-in: %s", enable)
    if enable:
        set_run_at_signin(f'"{exe}"')
    else:
        clear_run_at_signin()


def apply_shortcuts(
    identity: InstallerIdentity,
    install_dir: Path,
    *,
    create_desktop: bool,
    create_start_menu: bool,
) -> None:
    """Create the requested shortcuts and remove the ones now unwanted."""
    exe = install_dir / APP_EXE_NAME
    sp = get_shortcut_paths(identity)

    if create_desktop:
        create_shortcut(exe, sp.desktop_lnk, working_dir=install_dir)
    else:
        # If user unchecks during reinstall/upgrade, remove it.
        try:
            sp.desktop_lnk.unlink(missing_ok=True)
        except OSError:
            # A shortcut held open or on a disconnected profile share cannot be
            # removed. The install itself is unaffected, so leave the stale
            # shortcut rather than failing the operation over it.
            pass

    if create_start_menu:
        create_shortcut(exe, sp.start_menu_lnk, working_dir=install_dir)
    else:
        try:
            sp.start_menu_lnk.unlink(missing_ok=True)
        except OSError:
            # As for the desktop shortcut above: a stale entry is preferable to
            # a failed install.
            pass
