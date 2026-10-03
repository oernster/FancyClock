"""Version comparison, the operation rules, the CLI and the constants."""

from __future__ import annotations

from pathlib import Path

import pytest

from installer.cli import parse_args, wants_remove_user_data
from installer.constants import InstallerIdentity
from installer.state.model import InstalledInfo, InstallerState, Operation
from installer.state.versioning import compare_versions, parse_version
from installer.ui._main_window_types import UiSelections
from installer.ui.themes import DARK, LIGHT

OLDER = "1.2.0"
CURRENT = "1.3.0"
NEWER = "1.10.0"


def test_parse_version_strips_whitespace() -> None:
    parsed = parse_version(f"  {CURRENT} ")
    assert parsed.raw == CURRENT
    assert str(parsed.parsed) == CURRENT


@pytest.mark.parametrize("raw", ["not a version", "", None])
def test_unparseable_versions_read_as_very_old(raw: str | None) -> None:
    assert str(parse_version(raw).parsed) == "0.0.0"


@pytest.mark.parametrize(
    ("installer", "installed", "expected"),
    [(OLDER, CURRENT, -1), (CURRENT, CURRENT, 0), (NEWER, CURRENT, 1)],
)
def test_compare_versions(installer: str, installed: str, expected: int) -> None:
    assert compare_versions(installer, installed) == expected


def _state(installed_version: str | None) -> InstallerState:
    installed = (
        None
        if installed_version is None
        else InstalledInfo(version=installed_version, location=Path("C:/Apps/FC"))
    )
    return InstallerState(installer_version=CURRENT, installed=installed)


@pytest.mark.parametrize(
    ("installed_version", "expected"),
    [
        (None, {Operation.INSTALL}),
        (CURRENT, {Operation.REINSTALL, Operation.REPAIR, Operation.UNINSTALL}),
        (OLDER, {Operation.UPGRADE, Operation.UNINSTALL}),
        (NEWER, {Operation.REPAIR, Operation.UNINSTALL}),
    ],
)
def test_allowed_operations(
    installed_version: str | None, expected: set[Operation]
) -> None:
    assert _state(installed_version).allowed_operations() == frozenset(expected)


def test_status_line_when_not_installed() -> None:
    assert _state(None).status_line("Fancy Clock") == (
        "Fancy Clock is not installed on this user account."
    )


def test_status_line_names_the_installed_version_and_place() -> None:
    line = _state(OLDER).status_line("Fancy Clock")
    assert line.startswith(f"Fancy Clock v{OLDER} is already installed at ")
    assert str(Path("C:/Apps/FC")) in line


def test_parse_args_reads_every_flag() -> None:
    args = parse_args(
        ["--uninstall", "--repair", "--quiet", "--remove-user-data", "--keep-user-data"]
    )
    assert args.uninstall and args.repair and args.quiet
    assert args.remove_user_data and args.keep_user_data


def test_parse_args_defaults_are_off() -> None:
    args = parse_args([])
    assert not (args.uninstall or args.repair or args.quiet)


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--keep-user-data"], False),
        (["--keep-user-data", "--remove-user-data"], False),
        (["--remove-user-data"], True),
        ([], True),
    ],
)
def test_wants_remove_user_data(argv: list[str], expected: bool) -> None:
    assert wants_remove_user_data(parse_args(argv)) is expected


def test_installer_exe_path_sits_in_the_installer_subfolder(tmp_path: Path) -> None:
    identity = InstallerIdentity()
    assert identity.installer_exe_path(tmp_path) == (
        tmp_path / identity.installer_subdir / identity.installer_exe_name
    )


def test_themes_are_distinct_and_offer_the_other_one() -> None:
    assert {LIGHT.name, DARK.name} == {"light", "dark"}
    assert LIGHT.qss != DARK.qss
    assert LIGHT.toggle_label != DARK.toggle_label


def test_ui_selections_hold_what_the_user_chose(tmp_path: Path) -> None:
    chosen = UiSelections(
        install_dir=tmp_path,
        shortcut_desktop=True,
        shortcut_start_menu=False,
        start_on_signin=True,
    )
    assert chosen.install_dir == tmp_path
    assert chosen.shortcut_desktop and chosen.start_on_signin
    assert not chosen.shortcut_start_menu
