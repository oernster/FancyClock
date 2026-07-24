"""Autostart adapter tests: fakes for logic, a real HKCU key for winreg."""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

import pytest

from fancyclock.infrastructure.autostart import (
    LAUNCH_AGENT_LABEL,
    RUN_VALUE_NAME,
    LaunchAgentAutostart,
    NullAutostart,
    WindowsRunKeyAutostart,
    WinRegRunKey,
    XdgAutostart,
    is_flatpak,
    join_command,
)

TEST_KEY_PATH = r"Software\FancyClockTests\Run"


class FakeRunKey:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get_value(self, name: str) -> str | None:
        return self.values.get(name)

    def set_value(self, name: str, value: str) -> None:
        self.values[name] = value

    def delete_value(self, name: str) -> None:
        self.values.pop(name, None)


def test_join_command_quotes_only_parts_with_spaces() -> None:
    joined = join_command((r"C:\Program Files\FancyClock\FancyClock.exe", "--tray"))
    assert joined == r'"C:\Program Files\FancyClock\FancyClock.exe" --tray'


def test_is_flatpak_reads_the_environment_marker() -> None:
    assert is_flatpak({"FLATPAK_ID": "uk.codecrafter.FancyClock"})
    assert not is_flatpak({})
    assert isinstance(is_flatpak(), bool)


def test_null_autostart_is_inert() -> None:
    null = NullAutostart()
    assert not null.is_supported()
    assert not null.is_enabled()
    null.enable()
    null.disable()
    assert not null.is_enabled()


def test_windows_adapter_writes_and_removes_the_run_value() -> None:
    registry = FakeRunKey()
    adapter = WindowsRunKeyAutostart((r"C:\Apps\Fancy Clock\FancyClock.exe",), registry)
    assert adapter.is_supported()
    assert not adapter.is_enabled()

    adapter.enable()
    assert adapter.is_enabled()
    assert registry.values[RUN_VALUE_NAME] == r'"C:\Apps\Fancy Clock\FancyClock.exe"'

    adapter.disable()
    assert not adapter.is_enabled()
    assert RUN_VALUE_NAME not in registry.values


@pytest.mark.skipif(sys.platform != "win32", reason="winreg is Windows-only")
def test_winreg_run_key_roundtrips_against_a_test_key() -> None:
    key = WinRegRunKey(key_path=TEST_KEY_PATH)
    try:
        assert key.get_value("FancyClockProbe") is None
        key.delete_value("FancyClockProbe")

        key.set_value("FancyClockProbe", "C:\\probe.exe")
        assert key.get_value("FancyClockProbe") == "C:\\probe.exe"

        key.delete_value("FancyClockProbe")
        assert key.get_value("FancyClockProbe") is None
    finally:
        key.delete_value("FancyClockProbe")


def test_xdg_adapter_writes_and_removes_the_desktop_entry(tmp_path: Path) -> None:
    adapter = XdgAutostart(("/usr/bin/fancyclock",), home=tmp_path)
    assert adapter.is_supported()
    assert not adapter.is_enabled()

    adapter.enable()
    assert adapter.is_enabled()
    entry = (tmp_path / ".config/autostart/fancyclock.desktop").read_text(
        encoding="utf-8"
    )
    assert "Exec=/usr/bin/fancyclock" in entry
    assert "[Desktop Entry]" in entry

    adapter.disable()
    assert not adapter.is_enabled()
    adapter.disable()


def test_launch_agent_adapter_writes_and_removes_the_plist(tmp_path: Path) -> None:
    command = ("/Applications/FancyClock.app/Contents/MacOS/FancyClock",)
    adapter = LaunchAgentAutostart(command, home=tmp_path)
    assert adapter.is_supported()
    assert not adapter.is_enabled()

    adapter.enable()
    assert adapter.is_enabled()
    plist_path = tmp_path / "Library/LaunchAgents/uk.codecrafter.FancyClock.plist"
    with plist_path.open("rb") as f:
        document = plistlib.load(f)
    assert document["Label"] == LAUNCH_AGENT_LABEL
    assert document["ProgramArguments"] == list(command)
    assert document["RunAtLoad"] is True

    adapter.disable()
    assert not adapter.is_enabled()
