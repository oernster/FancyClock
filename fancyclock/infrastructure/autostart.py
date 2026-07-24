"""Start-on-sign-in adapters for Windows, macOS, Linux and sandboxes.

Each adapter implements the ``AutostartManager`` port. The composition
root picks the adapter for the running platform and injects the launch
command; under Flatpak the null adapter hides the feature (sandboxed
autostart needs the Background portal, deferred).
"""

from __future__ import annotations

import os
import plistlib
from pathlib import Path
from typing import Mapping, Protocol

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "FancyClock"
XDG_AUTOSTART_DIR = ".config/autostart"
XDG_DESKTOP_FILE = "fancyclock.desktop"
LAUNCH_AGENTS_DIR = "Library/LaunchAgents"
LAUNCH_AGENT_FILE = "uk.codecrafter.FancyClock.plist"
LAUNCH_AGENT_LABEL = "uk.codecrafter.FancyClock"
FLATPAK_ENV_MARKER = "FLATPAK_ID"

DESKTOP_TEMPLATE = """[Desktop Entry]
Type=Application
Name=Fancy Clock
Exec={command}
X-GNOME-Autostart-enabled=true
"""


def join_command(parts: tuple[str, ...]) -> str:
    """Join argv parts into one shell-style command string."""
    quoted = [f'"{part}"' if " " in part else part for part in parts]
    return " ".join(quoted)


def is_flatpak(env: Mapping[str, str] | None = None) -> bool:
    """Return whether the app is running inside a Flatpak sandbox."""
    environment = env if env is not None else os.environ
    return FLATPAK_ENV_MARKER in environment


class RunKeyRegistry(Protocol):
    """Minimal registry access needed by the Windows adapter."""

    def get_value(self, name: str) -> str | None:
        """Return the value ``name``, or ``None``."""
        ...

    def set_value(self, name: str, value: str) -> None:
        """Create or overwrite the value ``name``."""
        ...

    def delete_value(self, name: str) -> None:
        """Delete the value ``name`` if present."""
        ...


class WinRegRunKey:
    """Real HKCU registry access to a Run-style key via ``winreg``."""

    def __init__(self, key_path: str = RUN_KEY_PATH) -> None:
        import winreg

        self._winreg = winreg
        self._key_path = key_path

    def get_value(self, name: str) -> str | None:
        """Return the value ``name``, or ``None``."""
        reg = self._winreg
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER, self._key_path) as key:
                value, _ = reg.QueryValueEx(key, name)
                return str(value)
        except OSError:
            return None

    def set_value(self, name: str, value: str) -> None:
        """Create or overwrite the string value ``name``."""
        reg = self._winreg
        with reg.CreateKey(reg.HKEY_CURRENT_USER, self._key_path) as key:
            reg.SetValueEx(key, name, 0, reg.REG_SZ, value)

    def delete_value(self, name: str) -> None:
        """Delete the value ``name`` if present."""
        reg = self._winreg
        try:
            with reg.OpenKey(
                reg.HKEY_CURRENT_USER, self._key_path, 0, reg.KEY_SET_VALUE
            ) as key:
                reg.DeleteValue(key, name)
        except OSError:
            pass


class NullAutostart:
    """Autostart placeholder where the feature is unavailable."""

    def is_supported(self) -> bool:
        """Autostart cannot be managed here."""
        return False

    def is_enabled(self) -> bool:
        """Never enabled."""
        return False

    def enable(self) -> None:
        """No-op."""

    def disable(self) -> None:
        """No-op."""


class WindowsRunKeyAutostart:
    """Start-on-sign-in via the per-user HKCU Run key."""

    def __init__(self, command: tuple[str, ...], registry: RunKeyRegistry) -> None:
        self._command = join_command(command)
        self._registry = registry

    def is_supported(self) -> bool:
        """Supported on Windows."""
        return True

    def is_enabled(self) -> bool:
        """Return whether the Run value exists."""
        return self._registry.get_value(RUN_VALUE_NAME) is not None

    def enable(self) -> None:
        """Write the Run value."""
        self._registry.set_value(RUN_VALUE_NAME, self._command)

    def disable(self) -> None:
        """Remove the Run value."""
        self._registry.delete_value(RUN_VALUE_NAME)


class XdgAutostart:
    """Start-on-sign-in via an XDG autostart desktop entry."""

    def __init__(self, command: tuple[str, ...], home: Path) -> None:
        self._command = join_command(command)
        self._path = home / XDG_AUTOSTART_DIR / XDG_DESKTOP_FILE

    def is_supported(self) -> bool:
        """Supported on desktop Linux outside sandboxes."""
        return True

    def is_enabled(self) -> bool:
        """Return whether the desktop entry exists."""
        return self._path.is_file()

    def enable(self) -> None:
        """Write the desktop entry."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            DESKTOP_TEMPLATE.format(command=self._command), encoding="utf-8"
        )

    def disable(self) -> None:
        """Remove the desktop entry."""
        self._path.unlink(missing_ok=True)


class LaunchAgentAutostart:
    """Start-on-sign-in via a per-user macOS LaunchAgent."""

    def __init__(self, command: tuple[str, ...], home: Path) -> None:
        self._command = command
        self._path = home / LAUNCH_AGENTS_DIR / LAUNCH_AGENT_FILE

    def is_supported(self) -> bool:
        """Supported on macOS."""
        return True

    def is_enabled(self) -> bool:
        """Return whether the LaunchAgent plist exists."""
        return self._path.is_file()

    def enable(self) -> None:
        """Write the LaunchAgent plist."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "Label": LAUNCH_AGENT_LABEL,
            "ProgramArguments": list(self._command),
            "RunAtLoad": True,
        }
        with self._path.open("wb") as f:
            plistlib.dump(document, f)

    def disable(self) -> None:
        """Remove the LaunchAgent plist."""
        self._path.unlink(missing_ok=True)
