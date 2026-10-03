"""Repair against the manifest hashes, run inside tmp_path."""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from fancyclock.version import __version__
from installer.constants import InstallerIdentity
from installer.ops import repair_ops
from installer.ops.errors import AppRunningError, InstallerOperationError
from installer.ops.repair_ops import RepairOptions, repair
from installer.ops.shortcuts import get_shortcut_paths
from installer.state.registry import RUN_KEY, RUN_VALUE_NAME, write_uninstall_entry
from tests.installer.installer_fakes import Machine, RecordingProgress, stage_payload

IDENTITY = InstallerIdentity(uninstall_key=r"Software\FancyClockTests\Uninstall")

# One member per verification outcome the repair loop distinguishes.
PAYLOAD = {
    "FancyClock.exe": b"good executable",
    "_internal/intact.dll": b"intact library",
    "_internal/wrong_size.dll": b"right length here",
    "_internal/same_size.dll": b"same length text",
    "_internal/missing.dll": b"missing library",
    "_internal/bad_manifest.dll": b"bad manifest size",
}
ON_DISK = {
    "FancyClock.exe": PAYLOAD["FancyClock.exe"],
    "_internal/intact.dll": PAYLOAD["_internal/intact.dll"],
    "_internal/wrong_size.dll": b"short",
    "_internal/same_size.dll": b"SAME LENGTH TEXT",
    "_internal/bad_manifest.dll": PAYLOAD["_internal/bad_manifest.dll"],
}
RESTORED = sorted(name for name in PAYLOAD if ON_DISK.get(name) != PAYLOAD[name]) + [
    "_internal/bad_manifest.dll"
]


def _install(tmp_path: Path, *, version: str = "1.3.0", installer: str = "") -> Path:
    install_dir = tmp_path / "Programs" / "FancyClock"
    for name, data in ON_DISK.items():
        (install_dir / name).parent.mkdir(parents=True, exist_ok=True)
        (install_dir / name).write_bytes(data)
    write_uninstall_entry(
        IDENTITY.uninstall_key,
        display_name="Fancy Clock",
        display_version=version,
        install_location=install_dir,
        uninstall_string="setup.exe --uninstall",
        installer_path=installer,
    )
    return install_dir


@pytest.fixture
def payload(machine: Machine) -> Machine:
    stage_payload(
        machine.data_root,
        PAYLOAD,
        manifest_overrides={"_internal/bad_manifest.dll": {"size": "not a number"}},
    )
    return machine


def test_repair_restores_only_what_fails_verification(
    payload: Machine, tmp_path: Path
) -> None:
    install_dir = _install(tmp_path, installer="setup.exe")
    progress = RecordingProgress()

    repair(
        IDENTITY,
        RepairOptions(
            restore_desktop_shortcut=True,
            restore_start_menu_shortcut=False,
            restore_start_on_signin=True,
        ),
        progress=progress,
        cancel_event=threading.Event(),
    )

    for name, data in PAYLOAD.items():
        assert (install_dir / name).read_bytes() == data
    restored = sorted(
        str(u).removeprefix("Restoring ").removesuffix("...")
        for u in progress.updates
        if str(u).startswith("Restoring _internal")
    )
    assert restored == sorted(RESTORED)
    resolved = install_dir.resolve()
    exe = resolved / "FancyClock.exe"
    desktop = get_shortcut_paths(IDENTITY).desktop_lnk
    assert payload.shortcuts == [(exe, desktop, resolved)]
    assert payload.winreg.values(RUN_KEY)[RUN_VALUE_NAME] == f'"{exe}"'
    entry = payload.winreg.values(IDENTITY.uninstall_key)
    assert entry["DisplayVersion"] == "1.3.0"
    assert entry["InstallerPath"] == "setup.exe"
    assert entry["DisplayIcon"] == str(exe)


def test_repair_keeps_existing_shortcuts_and_fills_blank_metadata(
    payload: Machine, tmp_path: Path
) -> None:
    _install(tmp_path, version="")
    sp = get_shortcut_paths(IDENTITY)
    for link in (sp.desktop_lnk, sp.start_menu_lnk):
        link.parent.mkdir(parents=True, exist_ok=True)
        link.write_bytes(b"")
    payload.winreg.CreateKey(payload.winreg.HKEY_CURRENT_USER, RUN_KEY)

    repair(
        IDENTITY,
        RepairOptions(restore_desktop_shortcut=True, restore_start_menu_shortcut=True),
    )

    assert payload.shortcuts == []
    assert payload.winreg.values(RUN_KEY) == {}
    entry = payload.winreg.values(IDENTITY.uninstall_key)
    assert entry["DisplayVersion"] == __version__
    assert "InstallerPath" not in entry


def test_repair_restores_a_missing_start_menu_shortcut(
    payload: Machine, tmp_path: Path
) -> None:
    _install(tmp_path)

    repair(
        IDENTITY,
        RepairOptions(restore_desktop_shortcut=False, restore_start_menu_shortcut=True),
    )

    ((_, link, _),) = payload.shortcuts
    assert link == get_shortcut_paths(IDENTITY).start_menu_lnk


def test_repair_honours_cancel(payload: Machine, tmp_path: Path) -> None:
    install_dir = _install(tmp_path)
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(InstallerOperationError, match="Cancelled"):
        repair(
            IDENTITY,
            RepairOptions(
                restore_desktop_shortcut=False, restore_start_menu_shortcut=False
            ),
            cancel_event=cancel,
        )

    assert (install_dir / "_internal" / "wrong_size.dll").read_bytes() == b"short"


def test_repair_refuses_when_nothing_is_installed() -> None:
    with pytest.raises(InstallerOperationError, match="not installed"):
        repair(IDENTITY, RepairOptions(False, False))


def test_repair_refuses_when_the_folder_has_gone(tmp_path: Path) -> None:
    write_uninstall_entry(
        IDENTITY.uninstall_key,
        display_name="Fancy Clock",
        display_version="1.3.0",
        install_location=tmp_path / "gone",
        uninstall_string="setup.exe --uninstall",
    )

    with pytest.raises(InstallerOperationError, match="not installed"):
        repair(IDENTITY, RepairOptions(False, False))


def test_repair_refuses_while_the_app_runs(payload: Machine, tmp_path: Path) -> None:
    _install(tmp_path)
    payload.running = True

    with pytest.raises(AppRunningError):
        repair(IDENTITY, RepairOptions(False, False))


def test_repair_refuses_to_run_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repair_ops, "os", SimpleNamespace(name="posix"))

    with pytest.raises(InstallerOperationError, match="Windows-only"):
        repair(IDENTITY, RepairOptions(False, False))


def test_repair_without_an_executable_skips_the_running_check(
    payload: Machine, tmp_path: Path
) -> None:
    install_dir = _install(tmp_path)
    (install_dir / "FancyClock.exe").unlink()
    payload.running = True

    repair(IDENTITY, RepairOptions(False, False))

    assert (install_dir / "FancyClock.exe").read_bytes() == PAYLOAD["FancyClock.exe"]
