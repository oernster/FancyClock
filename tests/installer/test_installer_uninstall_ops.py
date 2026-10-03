"""Uninstall, run inside tmp_path against the fake hive.

The detached PowerShell helper is recorded by the isolation fixture rather than
started. The retry sleep is recorded rather than waited out.
"""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace

import pytest

from fancyclock.version import APP_NAME, ORGANIZATION_NAME
from installer.constants import InstallerIdentity
from installer.ops import uninstall_ops
from installer.ops.errors import AppRunningError, InstallerOperationError
from installer.ops.shortcuts import get_shortcut_paths
from installer.ops.uninstall_ops import (
    _DIRECT_DELETE_ATTEMPTS,
    _DIRECT_DELETE_INTERVAL_S,
    UninstallOptions,
    _delete_install_dir_now,
    _running_from_inside,
    _schedule_delete_after_exit,
    uninstall,
    uninstall_with_feedback,
)
from installer.state import registry
from installer.state.registry import RUN_KEY, RUN_VALUE_NAME, write_uninstall_entry
from tests.installer.installer_fakes import Machine, RecordingProgress

IDENTITY = InstallerIdentity(uninstall_key=r"Software\FancyClockTests\Uninstall")


def _installed(
    tmp_path: Path, *, desktop: bool | None = True, start_menu: bool | None = True
) -> Path:
    install_dir = tmp_path / "Programs" / "FancyClock"
    install_dir.mkdir(parents=True)
    (install_dir / "FancyClock.exe").write_bytes(b"exe")
    write_uninstall_entry(
        IDENTITY.uninstall_key,
        display_name="Fancy Clock",
        display_version="1.3.0",
        install_location=install_dir,
        uninstall_string="setup.exe --uninstall",
        shortcut_desktop=desktop,
        shortcut_start_menu=start_menu,
    )
    return install_dir


def _links() -> list[Path]:
    sp = get_shortcut_paths(IDENTITY)
    links = [sp.desktop_lnk, sp.start_menu_lnk, sp.taskbar_lnk]
    for link in links:
        link.parent.mkdir(parents=True, exist_ok=True)
        link.write_bytes(b"")
    return links


def _user_data(machine: Machine) -> Path:
    data = machine.local / ORGANIZATION_NAME / APP_NAME
    (data / "Cache").mkdir(parents=True)
    (data / "settings.json").write_text("{}", encoding="utf-8")
    return data


def test_uninstall_removes_everything_it_made(machine: Machine, tmp_path: Path) -> None:
    install_dir = _installed(tmp_path)
    links = _links()
    data = _user_data(machine)
    registry.set_run_at_signin("FancyClock.exe")

    uninstall(IDENTITY, UninstallOptions())

    assert not install_dir.exists()
    assert not any(link.exists() for link in links)
    assert not data.exists()
    assert IDENTITY.uninstall_key not in machine.winreg.keys
    assert RUN_VALUE_NAME not in machine.winreg.values(RUN_KEY)
    assert machine.detached == []


def test_uninstall_keeps_unrecorded_shortcuts_and_user_data(
    machine: Machine, tmp_path: Path
) -> None:
    _installed(tmp_path, desktop=False, start_menu=False)
    desktop, start_menu, taskbar = _links()
    data = _user_data(machine)

    uninstall(IDENTITY, UninstallOptions(remove_user_data=False))

    assert desktop.exists() and start_menu.exists()
    assert not taskbar.exists()
    assert data.exists()


def test_uninstall_with_only_a_location_removes_both_shortcuts(
    machine: Machine, tmp_path: Path
) -> None:
    install_dir = tmp_path / "Programs" / "FancyClock"
    install_dir.mkdir(parents=True)
    key = machine.winreg.CreateKey(
        machine.winreg.HKEY_CURRENT_USER, IDENTITY.uninstall_key
    )
    machine.winreg.SetValueEx(key, "InstallLocation", 0, "REG_SZ", str(install_dir))
    desktop, start_menu, _ = _links()

    uninstall(IDENTITY, UninstallOptions())

    assert not desktop.exists() and not start_menu.exists()
    assert not install_dir.exists()


def test_uninstall_refuses_when_nothing_is_installed() -> None:
    with pytest.raises(InstallerOperationError, match="not detected"):
        uninstall(IDENTITY, UninstallOptions())


def test_uninstall_refuses_while_the_app_runs(machine: Machine, tmp_path: Path) -> None:
    install_dir = _installed(tmp_path)
    machine.running = True

    with pytest.raises(AppRunningError):
        uninstall(IDENTITY, UninstallOptions())

    assert install_dir.exists()


def test_uninstall_refuses_to_run_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(uninstall_ops, "os", SimpleNamespace(name="posix"))

    with pytest.raises(InstallerOperationError, match="Windows-only"):
        uninstall(IDENTITY, UninstallOptions())


def test_registry_failures_do_not_stop_the_uninstall(
    machine: Machine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    install_dir = _installed(tmp_path)
    machine.winreg.delete_errors[IDENTITY.uninstall_key] = PermissionError("denied")

    def refuse() -> None:
        raise PermissionError("run key denied")

    monkeypatch.setattr(registry, "clear_run_at_signin", refuse)

    uninstall(IDENTITY, UninstallOptions())

    assert not install_dir.exists()
    assert IDENTITY.uninstall_key in machine.winreg.keys


def test_uninstaller_inside_the_folder_defers_the_delete(
    machine: Machine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    install_dir = _installed(tmp_path)
    inside = install_dir / "_installer" / "FancyClockSetup.exe"
    monkeypatch.setattr(uninstall_ops, "sys", SimpleNamespace(executable=str(inside)))

    uninstall(IDENTITY, UninstallOptions())

    assert install_dir.exists()
    assert len(machine.detached) == 1


def test_deferred_delete_runs_hidden_and_quotes_the_path(
    machine: Machine, tmp_path: Path
) -> None:
    folder = tmp_path / "Oliver's Apps"
    folder.mkdir()

    _schedule_delete_after_exit(folder)

    ((args, kwargs),) = machine.detached
    assert args[0] == "powershell.exe"
    assert "Hidden" in args
    assert str(folder.resolve()).replace("'", "''") in args[-1]
    assert kwargs["shell"] is False
    assert kwargs["creationflags"] & subprocess.DETACHED_PROCESS


def test_running_from_the_folder_itself_counts_as_inside(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(uninstall_ops, "sys", SimpleNamespace(executable=str(tmp_path)))

    assert _running_from_inside(tmp_path)
    assert not _running_from_inside(tmp_path / "elsewhere")


class _UnresolvablePath(type(Path())):
    def resolve(self, strict: bool = False) -> Path:
        raise OSError("unreachable volume")


def test_unresolvable_paths_take_the_safe_deferred_route(tmp_path: Path) -> None:
    assert _running_from_inside(_UnresolvablePath(tmp_path))


def test_direct_delete_of_a_missing_folder_is_quiet(tmp_path: Path) -> None:
    _delete_install_dir_now(tmp_path / "gone")


@pytest.fixture
def held() -> Iterator[ExitStack]:
    with ExitStack() as stack:
        yield stack


def test_direct_delete_retries_then_reports_a_locked_folder(
    machine: Machine, tmp_path: Path, held: ExitStack
) -> None:
    folder = tmp_path / "FancyClock"
    folder.mkdir()
    held.enter_context((folder / "locked.dll").open("wb"))

    with pytest.raises(InstallerOperationError, match="Could not remove"):
        _delete_install_dir_now(folder)

    assert machine.sleeps == [_DIRECT_DELETE_INTERVAL_S] * (_DIRECT_DELETE_ATTEMPTS - 1)


def test_feedback_wrapper_reports_progress(machine: Machine, tmp_path: Path) -> None:
    _installed(tmp_path)
    progress = RecordingProgress()

    uninstall_with_feedback(
        IDENTITY, UninstallOptions(), progress=progress, cancel_event=threading.Event()
    )

    assert progress.updates == [
        "Reading installation metadata...",
        "Uninstall scheduled. Closing...",
    ]


def test_feedback_wrapper_without_progress(tmp_path: Path) -> None:
    install_dir = _installed(tmp_path)

    uninstall_with_feedback(IDENTITY, UninstallOptions())

    assert not install_dir.exists()


def test_feedback_wrapper_honours_cancel(tmp_path: Path) -> None:
    install_dir = _installed(tmp_path)
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(InstallerOperationError, match="Cancelled"):
        uninstall_with_feedback(IDENTITY, UninstallOptions(), cancel_event=cancel)

    assert install_dir.exists()
