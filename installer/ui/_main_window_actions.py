"""Wiring and presentation for the installer's main window.

Signal wiring, the licence dialog, the install directory and the button states
that a given installer state allows. The side-effecting half (running an
operation and reporting its progress and result) lives in
``_main_window_operations``, which reads from here rather than the other way
round, so the two cannot form a cycle.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog, QFileDialog

from fancyclock.version import APP_DISPLAY_NAME, APP_NAME, __version__
from installer.state.model import InstalledInfo, InstallerState, Operation
from installer.ui.licence_dialog import InstallerLicenceDialog

APP_EXE_NAME = "FancyClock.exe"

if TYPE_CHECKING:  # pragma: no cover
    from installer.ui.main_window import InstallerMainWindow


def connect_signals(window: InstallerMainWindow) -> None:
    """Wire every control the window builds.

    Nothing is caught here. `build_installer_main_window_ui` creates all six
    controls unconditionally and runs before this, so a missing attribute is a
    wiring defect rather than a runtime condition: the AttributeError names the
    control that was not built, which is what a developer needs to see. These
    calls were each wrapped in a blind try/except that could only ever have
    hidden that defect and left a dead button in the shipped setup program.
    """
    window._licence_btn.clicked.connect(window._show_installer_licence)
    window._theme_toggle_btn.clicked.connect(window._toggle_theme)
    if getattr(window, "_browse_btn", None) is not None:
        window._browse_btn.clicked.connect(window._browse_install_dir)
    window._btn_primary_left.clicked.connect(
        lambda: window._request_operation(Operation.INSTALL)
    )
    window._btn_primary_right.clicked.connect(
        lambda: window._request_operation(Operation.REPAIR)
    )
    window._btn_uninstall.clicked.connect(
        lambda: window._request_operation(Operation.UNINSTALL)
    )


def show_installer_licence(window: InstallerMainWindow) -> None:
    # Keep a reference so the dialog is not garbage-collected immediately.
    existing = getattr(window, "_installer_licence_dialog", None)
    if isinstance(existing, QDialog):
        try:
            existing.raise_()
            existing.activateWindow()
            return
        except RuntimeError:
            # The Python wrapper outlives the C++ dialog when Qt has already
            # deleted it; touching it then raises RuntimeError. Fall
            # through and build a fresh one rather than showing nothing.
            pass
    dlg = InstallerLicenceDialog(parent=window)
    window._installer_licence_dialog = dlg

    def _clear_ref() -> None:
        # Same wrapper-outlives-widget case: if the window is already gone
        # there is no reference left to clear.
        try:
            if getattr(window, "_installer_licence_dialog", None) is dlg:
                window._installer_licence_dialog = None
        except RuntimeError:
            pass

    dlg.finished.connect(_clear_ref)

    # Non-blocking but modal.
    dlg.open()


def default_install_dir() -> Path:
    local = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local) / "Programs" / APP_NAME


def browse_install_dir(window: InstallerMainWindow) -> None:
    current = Path(
        window._install_dir_edit.text().strip() or str(default_install_dir())
    )
    chosen = QFileDialog.getExistingDirectory(
        window, "Select installation directory", str(current)
    )
    if chosen:
        window._install_dir_edit.setText(chosen)


def refresh_state(window: InstallerMainWindow) -> None:
    read_entry = getattr(window, "_read_uninstall_entry", None)
    if read_entry is None:
        from installer.state.registry import read_uninstall_entry as read_entry

    entry = read_entry(window._identity.uninstall_key)
    installed = None
    if entry and entry.install_location.exists():
        exe = entry.install_location / APP_EXE_NAME
        if exe.exists():
            installed = InstalledInfo(
                version=entry.display_version, location=entry.install_location
            )

    state = InstallerState(installer_version=__version__, installed=installed)
    window._state = state

    window._status_line.setText(state.status_line(APP_DISPLAY_NAME))

    allowed = state.allowed_operations()
    set_buttons_for_allowed_ops(window, allowed)

    # Set checkboxes to persisted values if available.
    if entry is not None:
        if entry.shortcut_desktop is not None:
            window._desktop_cb.setChecked(entry.shortcut_desktop)
        if entry.shortcut_start_menu is not None:
            window._startmenu_cb.setChecked(entry.shortcut_start_menu)
        if entry.start_on_signin is not None:
            window._signin_cb.setChecked(entry.start_on_signin)

        # On upgrade/reinstall, default directory to current install dir.
        window._install_dir_edit.setText(str(entry.install_location))


def set_buttons_for_allowed_ops(
    window: InstallerMainWindow,
    allowed: set[Operation] | frozenset[Operation],
) -> None:
    # Primary buttons are shown in the center row. We use up to two.
    # Uninstall is shown separately in red.
    window._btn_uninstall.setVisible(Operation.UNINSTALL in allowed)

    primary_ops: list[Operation] = [
        op
        for op in [
            Operation.INSTALL,
            Operation.UPGRADE,
            Operation.REINSTALL,
            Operation.REPAIR,
        ]
        if op in allowed
    ]
    left = primary_ops[0] if primary_ops else None
    right = primary_ops[1] if len(primary_ops) > 1 else None

    def _label(op: Operation) -> str:
        return {
            Operation.INSTALL: "Install",
            Operation.UPGRADE: "Upgrade",
            Operation.REINSTALL: "Reinstall",
            Operation.REPAIR: "Repair",
        }[op]

    if left is None:
        window._btn_primary_left.setVisible(False)
    else:
        window._btn_primary_left.setVisible(True)
        window._btn_primary_left.setText(_label(left))
        try:
            window._btn_primary_left.clicked.disconnect()
        except RuntimeError:
            # Qt raises when the signal has nothing connected yet, which is the
            # normal case the first time the state is refreshed.
            pass
        window._btn_primary_left.clicked.connect(
            lambda: window._request_operation(left)
        )

    if right is None:
        window._btn_primary_right.setVisible(False)
    else:
        window._btn_primary_right.setVisible(True)
        window._btn_primary_right.setText(_label(right))
        try:
            window._btn_primary_right.clicked.disconnect()
        except RuntimeError:
            # As above: nothing connected yet on the first refresh.
            pass
        window._btn_primary_right.clicked.connect(
            lambda: window._request_operation(right)
        )


def validate_install_dir(path: Path) -> bool:
    """Return whether the chosen directory can actually be written to.

    The answer is discovered by writing, because permissions, a read-only
    volume and a path that is really a file all present differently and none
    is reliably visible from a stat. Every one of them surfaces as OSError,
    which is the only failure this is asking about.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        test = path / ".fancyclock_installer_write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True
    except OSError:
        return False
