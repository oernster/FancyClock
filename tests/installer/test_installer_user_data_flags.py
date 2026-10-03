"""The uninstall user-data flags, from the command line to the files on disk.

The window's operation builder is driven with a plain stand-in that carries
the parsed arguments and the identity, then the uninstall it returns runs
inside the isolated machine, so the test sees what a launch with each flag
would leave behind.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from installer.cli import parse_args
from installer.state.model import Operation
from installer.ui._main_window_operations import operation_callable
from installer.ui._main_window_types import UiSelections
from installer.ui._main_window_uninstall import confirmation_text
from tests.installer.installer_fakes import Machine
from tests.installer.test_installer_uninstall_ops import (
    IDENTITY,
    _installed,
    _user_data,
)


@pytest.mark.parametrize(
    ("argv", "kept"),
    [
        (["--uninstall", "--keep-user-data"], True),
        (["--uninstall", "--remove-user-data"], False),
        (["--uninstall"], False),
    ],
)
def test_uninstall_flag_decides_whether_user_data_survives(
    machine: Machine, tmp_path: Path, argv: list[str], kept: bool
) -> None:
    install_dir = _installed(tmp_path)
    data = _user_data(machine)
    window = SimpleNamespace(_cli_args=parse_args(argv), _identity=IDENTITY)
    selections = UiSelections(
        install_dir=install_dir,
        shortcut_desktop=True,
        shortcut_start_menu=True,
        start_on_signin=False,
    )

    call, kwargs = operation_callable(window, Operation.UNINSTALL, selections)
    call(**kwargs)

    assert not install_dir.exists()
    assert data.exists() is kept


def test_confirmation_names_what_happens_to_user_data() -> None:
    assert "keep your user data" in confirmation_text(remove_user_data=False)
    assert "remove user data" in confirmation_text(remove_user_data=True)
