"""Install, upgrade and reinstall, run for real inside tmp_path."""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from installer.constants import InstallerIdentity
from installer.ops import install_ops
from installer.ops.errors import AppRunningError, InstallerOperationError
from installer.ops.install_ops import (
    InstallOptions,
    _progress,
    install_new,
    upgrade_or_reinstall,
)
from installer.ops.shortcuts import get_shortcut_paths
from installer.state.registry import RUN_KEY, RUN_VALUE_NAME
from tests.installer.installer_fakes import (
    APP_FILES,
    Machine,
    RecordingProgress,
    stage_payload,
)

IDENTITY = InstallerIdentity(uninstall_key=r"Software\FancyClockTests\Uninstall")
STAGES = [10, 45, 75, 90, 100]
FIXED_HEX = "f" * 32


@pytest.fixture
def payload(machine: Machine) -> Machine:
    stage_payload(machine.data_root)
    (machine.data_root / "fancyclock.ico").write_bytes(b"icon")
    return machine


def _options(target: Path, *, desktop: bool, start_menu: bool, signin: bool):
    return InstallOptions(
        target_dir=target,
        create_desktop_shortcut=desktop,
        create_start_menu_shortcut=start_menu,
        start_on_signin=signin,
    )


def _old_install(folder: Path) -> Path:
    folder.mkdir(parents=True)
    (folder / "FancyClock.exe").write_bytes(b"old executable")
    (folder / "old-only.txt").write_text("old", encoding="utf-8")
    return folder


def _only_child(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.parent.iterdir())


def test_install_new_places_registers_and_links(
    payload: Machine, tmp_path: Path
) -> None:
    target = (tmp_path / "Programs" / "FancyClock").resolve()
    progress = RecordingProgress()

    install_new(
        IDENTITY,
        _options(target, desktop=True, start_menu=False, signin=True),
        progress=progress,
        cancel_event=threading.Event(),
    )

    assert (target / "FancyClock.exe").read_bytes() == APP_FILES["FancyClock.exe"]
    assert (target / "_internal" / "core.dll").is_file()
    assert (target / "fancyclock.ico").is_file()
    assert IDENTITY.installer_exe_path(target).is_file()
    entry = payload.winreg.values(IDENTITY.uninstall_key)
    assert entry["InstallLocation"] == str(target)
    assert entry["DisplayIcon"] == str(target / "fancyclock.ico")
    assert entry["ShortcutDesktop"] == "1" and entry["StartOnSignIn"] == "1"
    assert payload.winreg.values(RUN_KEY)[RUN_VALUE_NAME] == (
        f'"{target / "FancyClock.exe"}"'
    )
    desktop = get_shortcut_paths(IDENTITY).desktop_lnk
    assert payload.shortcuts == [(target / "FancyClock.exe", desktop, target)]
    assert progress.percentages == STAGES
    assert _only_child(target) == ["FancyClock"]


def test_install_over_an_existing_folder_replaces_it(
    payload: Machine, tmp_path: Path
) -> None:
    target = _old_install(tmp_path / "Programs" / "FancyClock").resolve()

    install_new(
        IDENTITY, _options(target, desktop=False, start_menu=False, signin=False)
    )

    assert not (target / "old-only.txt").exists()
    assert (target / "FancyClock.exe").read_bytes() == APP_FILES["FancyClock.exe"]
    assert _only_child(target) == ["FancyClock"]


def test_cancelled_install_leaves_nothing_behind(
    payload: Machine, tmp_path: Path
) -> None:
    target = tmp_path / "Programs" / "FancyClock"
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(InstallerOperationError, match="Cancelled"):
        install_new(
            IDENTITY,
            _options(target, desktop=True, start_menu=True, signin=False),
            cancel_event=cancel,
        )

    assert list(target.parent.iterdir()) == []
    assert IDENTITY.uninstall_key not in payload.winreg.keys


def test_payload_without_its_runtime_is_refused(
    machine: Machine, tmp_path: Path
) -> None:
    stage_payload(machine.data_root, {"FancyClock.exe": b"exe only"})
    target = tmp_path / "FancyClock"

    with pytest.raises(InstallerOperationError, match="missing"):
        install_new(
            IDENTITY, _options(target, desktop=False, start_menu=False, signin=False)
        )

    assert list(tmp_path.glob(".fancyclock_staging*")) == []
    assert not target.exists()


def test_leftover_staging_folders_are_cleared_first(
    payload: Machine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixed = SimpleNamespace(uuid4=lambda: SimpleNamespace(hex=FIXED_HEX))
    monkeypatch.setattr(install_ops, "uuid", fixed)
    target = (tmp_path / "Programs" / "FancyClock").resolve()
    target.parent.mkdir()
    for kind in ("install", "upgrade"):
        stale = target.parent / f".fancyclock_staging.{kind}.{FIXED_HEX}"
        stale.mkdir()
        (stale / "stale.txt").write_text("stale", encoding="utf-8")
    options = _options(target, desktop=False, start_menu=False, signin=False)

    install_new(IDENTITY, options)
    assert not (target.parent / f".fancyclock_staging.install.{FIXED_HEX}").exists()
    upgrade_or_reinstall(IDENTITY, current_install_dir=target, opts=options)

    assert not (target.parent / f".fancyclock_staging.upgrade.{FIXED_HEX}").exists()
    assert not (target / "stale.txt").exists()
    assert _only_child(target) == ["FancyClock"]


def test_reinstall_in_place_refreshes_files_and_choices(
    payload: Machine, tmp_path: Path
) -> None:
    target = _old_install(tmp_path / "Programs" / "FancyClock").resolve()
    sp = get_shortcut_paths(IDENTITY)
    sp.desktop_lnk.write_bytes(b"")
    progress = RecordingProgress()

    upgrade_or_reinstall(
        IDENTITY,
        current_install_dir=target,
        opts=_options(target, desktop=False, start_menu=True, signin=False),
        progress=progress,
    )

    assert not (target / "old-only.txt").exists()
    assert not sp.desktop_lnk.exists()
    assert payload.shortcuts == [(target / "FancyClock.exe", sp.start_menu_lnk, target)]
    assert RUN_VALUE_NAME not in payload.winreg.keys.get(RUN_KEY, {})
    assert progress.percentages == STAGES


def test_upgrade_to_a_new_folder_removes_the_old_one(
    payload: Machine, tmp_path: Path
) -> None:
    current = _old_install(tmp_path / "old" / "FancyClock")
    target = tmp_path / "new" / "FancyClock"

    upgrade_or_reinstall(
        IDENTITY,
        current_install_dir=current,
        opts=_options(target, desktop=False, start_menu=False, signin=True),
    )

    assert not current.exists()
    assert (target / "FancyClock.exe").read_bytes() == APP_FILES["FancyClock.exe"]
    entry = payload.winreg.values(IDENTITY.uninstall_key)
    assert entry["InstallLocation"] == str(target.resolve())


def test_upgrade_refuses_while_the_app_runs(payload: Machine, tmp_path: Path) -> None:
    current = _old_install(tmp_path / "FancyClock")
    payload.running = True

    with pytest.raises(AppRunningError):
        upgrade_or_reinstall(
            IDENTITY,
            current_install_dir=current,
            opts=_options(current, desktop=False, start_menu=False, signin=False),
        )

    assert (current / "old-only.txt").exists()


def test_upgrade_skips_the_running_check_without_an_executable(
    payload: Machine, tmp_path: Path
) -> None:
    current = tmp_path / "FancyClock"
    current.mkdir()
    payload.running = True

    upgrade_or_reinstall(
        IDENTITY,
        current_install_dir=current,
        opts=_options(current, desktop=False, start_menu=False, signin=False),
    )

    assert (current / "FancyClock.exe").is_file()


def test_progress_passes_bare_messages_through() -> None:
    progress = RecordingProgress()

    _progress(progress, pct=None, message="plain")
    _progress(None, pct=1, message="ignored")

    assert progress.updates == ["plain"]


def test_failed_upgrade_clears_its_staging_folder(
    machine: Machine, tmp_path: Path
) -> None:
    stage_payload(machine.data_root, {"FancyClock.exe": b"exe only"})
    current = _old_install(tmp_path / "Programs" / "FancyClock")

    with pytest.raises(InstallerOperationError, match="missing"):
        upgrade_or_reinstall(
            IDENTITY,
            current_install_dir=current,
            opts=_options(current, desktop=False, start_menu=False, signin=False),
        )

    assert _only_child(current) == ["FancyClock"]
    assert (current / "old-only.txt").exists()
