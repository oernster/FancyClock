"""Hand-written stand-ins for the setup program's operating-system seams.

The installer reaches the machine through a handful of narrow doors: the
``winreg`` module, the Shell Link shortcut writer, process detection, the
detached delete helper and a sleep between delete retries. These fakes stand at
those doors so the logic behind them runs for real against ``tmp_path`` while
nothing touches the registry, the Start Menu, the Desktop or the process table.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

PAYLOAD_RELATIVE_DIR = Path("installer") / "payload"
PAYLOAD_ZIP_NAME = "payload.zip"
MANIFEST_NAME = "manifest.json"

# A minimal bundle with the two members the installer insists on.
APP_FILES: dict[str, bytes] = {
    "FancyClock.exe": b"stand-in executable",
    "_internal/core.dll": b"stand-in runtime library",
}


class FakeKey:
    """An open registry key handle, usable as a context manager."""

    def __init__(self, path: str) -> None:
        self.path = path

    def __enter__(self) -> FakeKey:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


class FakeWinreg:
    """An in-memory HKCU hive exposing the slice of ``winreg`` the code uses.

    Missing keys and values raise ``FileNotFoundError`` exactly as the real
    module does. ``delete_errors`` and ``open_errors`` let a test make one key
    refuse a call with a chosen ``OSError``. Method names copy the winreg API.
    """

    HKEY_CURRENT_USER = "HKEY_CURRENT_USER"
    REG_SZ = "REG_SZ"
    REG_DWORD = "REG_DWORD"
    KEY_SET_VALUE = "KEY_SET_VALUE"

    def __init__(self) -> None:
        self.keys: dict[str, dict[str, tuple[object, str]]] = {}
        self.delete_errors: dict[str, OSError] = {}
        self.open_errors: dict[str, OSError] = {}

    def OpenKey(
        self, root: str, sub_key: str, reserved: int = 0, access: str = ""
    ) -> FakeKey:
        if sub_key in self.open_errors:
            raise self.open_errors[sub_key]
        if sub_key not in self.keys:
            raise FileNotFoundError(sub_key)
        return FakeKey(sub_key)

    def CreateKey(self, root: str, sub_key: str) -> FakeKey:
        self.keys.setdefault(sub_key, {})
        return FakeKey(sub_key)

    def QueryValueEx(self, key: FakeKey, name: str) -> tuple[object, str]:
        values = self.keys[key.path]
        if name not in values:
            raise FileNotFoundError(name)
        return values[name]

    def SetValueEx(
        self, key: FakeKey, name: str, reserved: int, kind: str, value: object
    ) -> None:
        self.keys[key.path][name] = (value, kind)

    def DeleteKey(self, root: str, sub_key: str) -> None:
        if sub_key in self.delete_errors:
            raise self.delete_errors[sub_key]
        if sub_key not in self.keys:
            raise FileNotFoundError(sub_key)
        del self.keys[sub_key]

    def DeleteValue(self, key: FakeKey, name: str) -> None:
        values = self.keys[key.path]
        if name not in values:
            raise FileNotFoundError(name)
        del values[name]

    def values(self, sub_key: str) -> dict[str, object]:
        """Return the plain values stored under ``sub_key``."""
        return {name: value for name, (value, _) in self.keys[sub_key].items()}


@dataclass
class Machine:
    """Everything the isolation fixture redirected, for tests to inspect."""

    home: Path
    local: Path
    roaming: Path
    data_root: Path
    winreg: FakeWinreg
    running: bool = False
    shortcuts: list[tuple[Path, Path, Path | None]] = field(default_factory=list)
    detached: list[tuple[list[str], dict[str, object]]] = field(default_factory=list)
    sleeps: list[float] = field(default_factory=list)

    def record_shortcut(
        self, target_exe: Path, shortcut_path: Path, *, working_dir: Path | None = None
    ) -> None:
        """Stand in for the COM shortcut writer: record it, leave a file."""
        self.shortcuts.append((target_exe, shortcut_path, working_dir))
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)
        shortcut_path.write_bytes(b"")

    def is_running(self, exe: Path) -> bool:
        """Stand in for process detection."""
        return self.running

    def popen(self, args: list[str], **kwargs: object) -> None:
        """Stand in for subprocess.Popen: record the command, start nothing."""
        self.detached.append((list(args), kwargs))

    def sleep(self, seconds: float) -> None:
        """Stand in for time.sleep: record the wait, do not wait."""
        self.sleeps.append(seconds)


@dataclass
class RecordingProgress:
    """Collects whatever an operation reports through its progress callback."""

    updates: list[object] = field(default_factory=list)

    def __call__(self, update: object) -> None:
        self.updates.append(update)

    @property
    def percentages(self) -> list[int]:
        return [u["pct"] for u in self.updates if isinstance(u, dict)]


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stage_payload(
    data_root: Path,
    files: Mapping[str, bytes] = APP_FILES,
    *,
    version: str = "9.9.9",
    manifest_overrides: Mapping[str, Mapping[str, object]] | None = None,
) -> Path:
    """Write payload.zip and manifest.json where resource_path will find them."""
    payload_dir = data_root / PAYLOAD_RELATIVE_DIR
    payload_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    with zipfile.ZipFile(payload_dir / PAYLOAD_ZIP_NAME, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
            entry = {"path": name, "size": len(data), "sha256": sha256_of(data)}
            entry.update((manifest_overrides or {}).get(name, {}))
            entries.append(entry)
    manifest = {"installer_version": version, "entries": entries}
    (payload_dir / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return payload_dir
