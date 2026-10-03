"""Keep every installer test off the real machine.

The fixture here is autouse, so no test in this folder can forget it. It
redirects the per-user profile into ``tmp_path``, swaps ``winreg`` for an
in-memory hive, points the bundled data root at a scratch directory and
replaces the four calls that would reach the operating system (the COM
shortcut writer, process detection, the detached delete helper and the retry
sleep) with recorders.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from installer.ops import (
    desktop_integration,
    install_ops,
    repair_ops,
    shortcuts,
    uninstall_ops,
)
from tests.installer.installer_fakes import FakeWinreg, Machine


@pytest.fixture(autouse=True)
def machine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Machine:
    home = tmp_path / "profile"
    local = home / "AppData" / "Local"
    roaming = home / "AppData" / "Roaming"
    data_root = tmp_path / "bundle-data"
    for directory in (home / "Desktop", local, roaming, data_root):
        directory.mkdir(parents=True)

    fake = Machine(
        home=home,
        local=local,
        roaming=roaming,
        data_root=data_root,
        winreg=FakeWinreg(),
    )

    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.setitem(sys.modules, "winreg", fake.winreg)
    monkeypatch.setattr(sys, "_MEIPASS", str(data_root), raising=False)

    for module in (shortcuts, desktop_integration, repair_ops):
        monkeypatch.setattr(module, "create_shortcut", fake.record_shortcut)
    for module in (install_ops, uninstall_ops, repair_ops):
        monkeypatch.setattr(module, "is_app_running", fake.is_running)

    monkeypatch.setattr(uninstall_ops.subprocess, "Popen", fake.popen)
    monkeypatch.setattr(uninstall_ops, "time", SimpleNamespace(sleep=fake.sleep))
    monkeypatch.setattr(
        uninstall_ops, "user_data_dir", lambda app, org: str(local / org / app)
    )
    monkeypatch.setattr(
        uninstall_ops,
        "user_cache_dir",
        lambda app, org: str(local / org / app / "Cache"),
    )
    return fake
