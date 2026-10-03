"""Desktop integration and the Qt-free half of the shortcut module.

The COM shortcut writer itself is replaced by the isolation fixture's
recorder; everything here is path logic and file removal inside tmp_path.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from installer.constants import InstallerIdentity
from installer.ops import shortcuts
from installer.ops.desktop_integration import (
    APP_EXE_NAME,
    DEPLOYED_ICO_NAME,
    DEPLOYED_PNG_NAMES,
    apply_shortcuts,
    deploy_runtime_icon_assets,
    register_uninstall,
)
from installer.ops.shortcuts import (
    _default_icon_location_for,
    get_shortcut_paths,
    remove_shortcut,
    remove_taskbar_pin,
)
from tests.installer.installer_fakes import Machine

IDENTITY = InstallerIdentity(uninstall_key=r"Software\FancyClockTests\Uninstall")


def test_register_uninstall_falls_back_to_the_exe_icon(
    machine: Machine, tmp_path: Path
) -> None:
    register_uninstall(
        IDENTITY,
        install_dir=tmp_path,
        installer_copy=tmp_path / "setup.exe",
        shortcut_desktop=False,
        shortcut_start_menu=True,
        start_on_signin=False,
    )

    entry = machine.winreg.values(IDENTITY.uninstall_key)
    assert entry["DisplayIcon"] == str(tmp_path / APP_EXE_NAME)
    assert entry["UninstallString"] == f'"{tmp_path / "setup.exe"}" --uninstall'
    assert entry["InstallerPath"] == str(tmp_path / "setup.exe")


def test_icon_assets_present_in_the_bundle_are_deployed(
    machine: Machine, tmp_path: Path
) -> None:
    shipped = DEPLOYED_PNG_NAMES[:2]
    for name in (DEPLOYED_ICO_NAME, *shipped):
        (machine.data_root / name).write_bytes(name.encode())
    install_dir = tmp_path / "Programs"
    install_dir.mkdir()

    deploy_runtime_icon_assets(install_dir=install_dir)

    assert sorted(p.name for p in install_dir.iterdir()) == sorted(
        (DEPLOYED_ICO_NAME, *shipped)
    )


def test_icon_copy_failures_are_cosmetic(machine: Machine, tmp_path: Path) -> None:
    for name in (DEPLOYED_ICO_NAME, DEPLOYED_PNG_NAMES[0]):
        (machine.data_root / name).write_bytes(b"icon")
    missing = tmp_path / "not-created"

    deploy_runtime_icon_assets(install_dir=missing)

    assert not missing.exists()


def test_no_icons_in_the_bundle_deploys_nothing(tmp_path: Path) -> None:
    deploy_runtime_icon_assets(install_dir=tmp_path)

    assert not (tmp_path / DEPLOYED_ICO_NAME).exists()


def test_unwanted_shortcuts_are_removed(machine: Machine, tmp_path: Path) -> None:
    sp = get_shortcut_paths(IDENTITY)
    for link in (sp.desktop_lnk, sp.start_menu_lnk):
        link.parent.mkdir(parents=True, exist_ok=True)
        link.write_bytes(b"")

    apply_shortcuts(IDENTITY, tmp_path, create_desktop=False, create_start_menu=False)

    assert not sp.desktop_lnk.exists() and not sp.start_menu_lnk.exists()
    assert machine.shortcuts == []


def test_shortcuts_that_cannot_be_removed_are_left(tmp_path: Path) -> None:
    sp = get_shortcut_paths(IDENTITY)
    for link in (sp.desktop_lnk, sp.start_menu_lnk):
        link.mkdir(parents=True)

    apply_shortcuts(IDENTITY, tmp_path, create_desktop=False, create_start_menu=False)

    assert sp.desktop_lnk.is_dir() and sp.start_menu_lnk.is_dir()


def test_shortcut_paths_live_in_the_user_profile(machine: Machine) -> None:
    sp = get_shortcut_paths(IDENTITY)
    programs = machine.roaming / "Microsoft" / "Windows" / "Start Menu" / "Programs"

    assert sp.desktop_lnk == machine.home / "Desktop" / "Fancy Clock.lnk"
    assert sp.start_menu_lnk == programs / "FancyClock" / "Fancy Clock.lnk"
    assert sp.taskbar_lnk.parent.name == "TaskBar"
    assert sp.taskbar_lnk.is_relative_to(machine.roaming)


def test_shortcut_paths_fall_back_to_the_roaming_profile(
    machine: Machine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("APPDATA")

    assert get_shortcut_paths(IDENTITY).start_menu_lnk.is_relative_to(machine.roaming)


def test_shortcuts_refuse_to_run_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shortcuts, "os", SimpleNamespace(name="posix"))

    with pytest.raises(RuntimeError, match="Windows only"):
        get_shortcut_paths(IDENTITY)


def test_icon_location_prefers_the_deployed_ico(tmp_path: Path) -> None:
    (tmp_path / DEPLOYED_ICO_NAME).write_bytes(b"icon")

    location = _default_icon_location_for(tmp_path / APP_EXE_NAME)

    assert location == str((tmp_path / DEPLOYED_ICO_NAME).resolve()).replace("\\", "/")


def test_icon_location_falls_back_to_the_exe(tmp_path: Path) -> None:
    (tmp_path / DEPLOYED_ICO_NAME).mkdir()
    exe = tmp_path / APP_EXE_NAME

    assert _default_icon_location_for(exe) == str(exe)


class _UnresolvablePath(type(Path())):
    def resolve(self, strict: bool = False) -> Path:
        raise OSError("unreachable volume")


def test_icon_location_survives_an_unresolvable_path(tmp_path: Path) -> None:
    exe = _UnresolvablePath(tmp_path / APP_EXE_NAME)

    assert _default_icon_location_for(exe) == str(exe)


def test_remove_shortcut_tidies_an_emptied_folder(tmp_path: Path) -> None:
    link = tmp_path / "Programs" / "FancyClock" / "Fancy Clock.lnk"
    link.parent.mkdir(parents=True)
    link.write_bytes(b"")

    remove_shortcut(link)

    assert not link.parent.exists()


def test_remove_shortcut_keeps_a_shared_folder(tmp_path: Path) -> None:
    link = tmp_path / "Fancy Clock.lnk"
    (tmp_path / "someone-else.lnk").write_bytes(b"")

    remove_shortcut(link)

    assert (tmp_path / "someone-else.lnk").exists()


def test_remove_shortcut_with_no_folder_is_quiet(tmp_path: Path) -> None:
    remove_shortcut(tmp_path / "gone" / "Fancy Clock.lnk")

    assert not (tmp_path / "gone").exists()


def test_remove_shortcut_gives_up_on_an_unremovable_link(tmp_path: Path) -> None:
    link = tmp_path / "Fancy Clock.lnk"
    link.mkdir()

    remove_shortcut(link)

    assert link.is_dir()


def test_remove_shortcut_leaves_a_folder_in_use(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    folder = tmp_path / "FancyClock"
    folder.mkdir()
    monkeypatch.chdir(folder)

    remove_shortcut(folder / "Fancy Clock.lnk")

    assert folder.is_dir()


def test_taskbar_pin_is_removed_and_its_folder_kept(tmp_path: Path) -> None:
    pin = tmp_path / "TaskBar" / "Fancy Clock.lnk"
    pin.parent.mkdir()
    pin.write_bytes(b"")
    locked = tmp_path / "TaskBar" / "Locked.lnk"
    locked.mkdir()

    remove_taskbar_pin(pin)
    remove_taskbar_pin(locked)

    assert not pin.exists()
    assert pin.parent.is_dir() and locked.is_dir()
