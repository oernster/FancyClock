"""The HKCU uninstall entry and Run value, driven through the fake hive."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from installer.state import registry
from installer.state.registry import (
    RUN_KEY,
    RUN_VALUE_NAME,
    _parse_bool,
    clear_run_at_signin,
    delete_uninstall_entry,
    read_uninstall_entry,
    set_run_at_signin,
    try_read_install_location,
    write_uninstall_entry,
)
from tests.installer.installer_fakes import Machine

KEY = r"Software\FancyClockTests\Uninstall"


def _write_full(location: Path) -> None:
    write_uninstall_entry(
        KEY,
        display_name="Fancy Clock",
        display_version="1.3.0",
        install_location=location,
        uninstall_string='"setup.exe" --uninstall',
        display_icon="icon.ico",
        publisher="Oliver Ernster",
        shortcut_desktop=True,
        shortcut_start_menu=False,
        start_on_signin=True,
        installer_path="setup.exe",
    )


def test_full_entry_round_trips(machine: Machine, tmp_path: Path) -> None:
    _write_full(tmp_path)

    entry = read_uninstall_entry(KEY)

    assert entry is not None
    assert entry.display_name == "Fancy Clock"
    assert entry.display_version == "1.3.0"
    assert entry.install_location == tmp_path
    assert entry.display_icon == "icon.ico"
    assert entry.publisher == "Oliver Ernster"
    assert entry.shortcut_desktop is True
    assert entry.shortcut_start_menu is False
    assert entry.start_on_signin is True
    assert entry.installer_path == "setup.exe"
    stored = machine.winreg.values(KEY)
    assert stored["NoModify"] == 1 and stored["NoRepair"] == 1
    assert len(str(stored["InstallDate"])) == len("YYYYMMDD")


def test_minimal_entry_leaves_the_optional_values_out(
    machine: Machine, tmp_path: Path
) -> None:
    write_uninstall_entry(
        KEY,
        display_name="Fancy Clock",
        display_version="",
        install_location=tmp_path,
        uninstall_string="setup.exe --uninstall",
    )

    stored = machine.winreg.values(KEY)
    for absent in (
        "DisplayIcon",
        "Publisher",
        "ShortcutDesktop",
        "ShortcutStartMenu",
        "StartOnSignIn",
        "InstallerPath",
    ):
        assert absent not in stored
    entry = read_uninstall_entry(KEY)
    assert entry is not None
    assert entry.display_icon is None and entry.shortcut_desktop is None


def test_false_flags_are_stored_as_zero(machine: Machine, tmp_path: Path) -> None:
    write_uninstall_entry(
        KEY,
        display_name="Fancy Clock",
        display_version="1.3.0",
        install_location=tmp_path,
        uninstall_string="setup.exe --uninstall",
        shortcut_desktop=False,
        shortcut_start_menu=True,
        start_on_signin=False,
    )

    stored = machine.winreg.values(KEY)
    assert stored["ShortcutDesktop"] == "0"
    assert stored["ShortcutStartMenu"] == "1"
    assert stored["StartOnSignIn"] == "0"


def test_absent_key_reads_as_not_installed() -> None:
    assert read_uninstall_entry(KEY) is None
    assert try_read_install_location(KEY) is None


def test_entry_missing_a_required_value_reads_as_not_installed(
    machine: Machine,
) -> None:
    key = machine.winreg.CreateKey(machine.winreg.HKEY_CURRENT_USER, KEY)
    machine.winreg.SetValueEx(key, "DisplayName", 0, "REG_SZ", "Fancy Clock")

    assert read_uninstall_entry(KEY) is None


def test_relative_install_location_reads_as_not_installed(tmp_path: Path) -> None:
    _write_full(Path("relative") / "dir")

    assert read_uninstall_entry(KEY) is None


def test_install_location_alone_is_still_found(machine: Machine) -> None:
    key = machine.winreg.CreateKey(machine.winreg.HKEY_CURRENT_USER, KEY)
    machine.winreg.SetValueEx(key, "InstallLocation", 0, "REG_SZ", "C:/Apps/FC")

    assert read_uninstall_entry(KEY) is None
    assert try_read_install_location(KEY) == Path("C:/Apps/FC")


def test_key_without_install_location_gives_no_location(machine: Machine) -> None:
    machine.winreg.CreateKey(machine.winreg.HKEY_CURRENT_USER, KEY)

    assert try_read_install_location(KEY) is None


def test_delete_removes_the_entry(tmp_path: Path) -> None:
    _write_full(tmp_path)

    delete_uninstall_entry(KEY)

    assert read_uninstall_entry(KEY) is None


def test_deleting_an_absent_entry_is_quiet() -> None:
    delete_uninstall_entry(KEY)


def test_delete_failure_other_than_absence_propagates(
    machine: Machine, tmp_path: Path
) -> None:
    _write_full(tmp_path)
    machine.winreg.delete_errors[KEY] = PermissionError("access denied")

    with pytest.raises(PermissionError):
        delete_uninstall_entry(KEY)


def test_run_value_is_written_and_cleared(machine: Machine) -> None:
    set_run_at_signin('"C:/Apps/FC/FancyClock.exe"')
    assert machine.winreg.values(RUN_KEY)[RUN_VALUE_NAME] == (
        '"C:/Apps/FC/FancyClock.exe"'
    )

    clear_run_at_signin()

    assert RUN_VALUE_NAME not in machine.winreg.values(RUN_KEY)


def test_clearing_an_absent_run_value_is_quiet(machine: Machine) -> None:
    clear_run_at_signin()
    machine.winreg.CreateKey(machine.winreg.HKEY_CURRENT_USER, RUN_KEY)
    clear_run_at_signin()

    assert machine.winreg.values(RUN_KEY) == {}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("1", True),
        (" TRUE ", True),
        ("on", True),
        ("0", False),
        ("No", False),
        ("off", False),
        ("maybe", None),
    ],
)
def test_parse_bool(raw: str | None, expected: bool | None) -> None:
    assert _parse_bool(raw) is expected


def test_registry_refuses_to_run_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, "os", SimpleNamespace(name="posix"))

    with pytest.raises(RuntimeError, match="Windows only"):
        read_uninstall_entry(KEY)
