"""Running an installer operation and reporting it back to the window.

This is the side-effecting half of the main window's behaviour: reading the
form into a selections value, choosing the operation to run, starting it on the
worker, then reflecting its progress, its interruptions and its result. The
presentation half (wiring, the licence dialog, the install directory and the
button states for a given installer state) stays in ``_main_window_actions``.

The split is one-way. This module reads three helpers from that one and nothing
there reads anything here, so the import direction cannot become a cycle.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from fancyclock.version import APP_DISPLAY_NAME
from installer.ops.errors import InstallerOperationError
from installer.ops.install_ops import InstallOptions, install_new, upgrade_or_reinstall
from installer.ops.repair_ops import RepairOptions, repair
from installer.ops.uninstall_ops import UninstallOptions, uninstall_with_feedback
from installer.state.model import Operation
from installer.ui._main_window_actions import (
    default_install_dir,
    refresh_state,
    validate_install_dir,
)
from installer.ui._main_window_types import UiSelections

if TYPE_CHECKING:  # pragma: no cover
    from installer.ui.main_window import InstallerMainWindow


def current_selections(window: InstallerMainWindow) -> UiSelections:
    p = Path(window._install_dir_edit.text().strip() or str(default_install_dir()))
    return UiSelections(
        install_dir=p,
        shortcut_desktop=bool(window._desktop_cb.isChecked()),
        shortcut_start_menu=bool(window._startmenu_cb.isChecked()),
        start_on_signin=bool(window._signin_cb.isChecked()),
    )


def request_operation(window: InstallerMainWindow, op: Operation) -> None:
    selections = current_selections(window)
    if op in {Operation.INSTALL, Operation.UPGRADE, Operation.REINSTALL}:
        if not validate_install_dir(selections.install_dir):
            QMessageBox.critical(
                window,
                "Invalid installation directory",
                "The selected installation directory is not writable without "
                "administrator privileges.",
            )
            return

    if window._op_controller.is_running:
        return

    # Immediately reflect that the operation has begun.
    # This also forces a re-read of the registry after install/uninstall so
    # button states update without requiring a relaunch.
    refresh_state(window)

    window._set_ui_busy(True)
    window._progress.setText("Working...")
    window._progress_bar.setValue(0)

    fn, kwargs = operation_callable(window, op, selections)
    window._debug_last_op = op
    window._debug_last_kwargs = kwargs
    window._op_controller.start(
        fn,
        kwargs=kwargs,
        on_progress=window._on_progress,
        on_finished=lambda r: window._on_operation_finished(op, r),
        on_app_running=lambda msg: window._on_app_running(op, msg),
    )


def on_progress(window: InstallerMainWindow, payload) -> None:  # noqa: ANN001
    # payload can be:
    # - str message
    # - {"pct": int, "message": str}
    if isinstance(payload, dict):
        pct = payload.get("pct")
        msg = payload.get("message", "")
        if isinstance(pct, int):
            window._progress_bar.setValue(max(0, min(100, pct)))
        if msg:
            window._progress.setText(str(msg))
        return

    if isinstance(payload, str) and payload:
        window._progress.setText(payload)


def set_ui_busy(window: InstallerMainWindow, busy: bool) -> None:
    window._progress_bar.setVisible(busy)
    for w in [
        window._btn_primary_left,
        window._btn_primary_right,
        window._btn_uninstall,
        window._licence_btn,
        window._theme_toggle_btn,
        window._install_dir_edit,
        window._desktop_cb,
        window._startmenu_cb,
    ]:
        w.setEnabled(not busy)


def on_app_running(window: InstallerMainWindow, op: Operation, msg: str) -> None:
    del msg

    window._set_ui_busy(False)
    window._progress.setText("")
    box = QMessageBox(window)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle(f"{APP_DISPLAY_NAME} is running")
    box.setText(f"Please close {APP_DISPLAY_NAME} and click Retry.")
    retry = box.addButton("Retry", QMessageBox.AcceptRole)
    box.addButton("Cancel", QMessageBox.RejectRole)
    box.exec()
    if box.clickedButton() == retry:
        window._request_operation(op)


def on_operation_finished(
    window: InstallerMainWindow,
    op: Operation,
    result,
) -> None:  # noqa: ANN001
    window._set_ui_busy(False)
    if result.ok:
        window._progress_bar.setValue(100)
        if op == Operation.UNINSTALL:
            window._progress.setText("Uninstalled")
        else:
            window._progress.setText("Done")
    else:
        if result.message and result.message != "app_running":
            QMessageBox.critical(window, "Operation failed", result.message)
        window._progress.setText("")
        window._progress_bar.setValue(0)

    refresh_state(window)

    # Keep completion visible briefly so users can tell something happened.
    try:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1200, lambda: window._progress.setText(""))
    except Exception:
        pass

    if op == Operation.UNINSTALL and result.ok:
        # Only auto-close when we were explicitly launched as an uninstaller
        # (e.g. from Windows Settings via UninstallString).
        if getattr(window._cli_args, "uninstall", False):
            try:
                from PySide6.QtCore import QTimer

                QTimer.singleShot(600, window.close)
            except Exception:
                window.close()
        return


def operation_callable(
    window: InstallerMainWindow,
    op: Operation,
    selections: UiSelections,
):
    read_entry = getattr(window, "_read_uninstall_entry", None)
    if read_entry is None:
        from installer.state.registry import read_uninstall_entry as read_entry

    entry = read_entry(window._identity.uninstall_key)
    current_install_dir = entry.install_location if entry else None

    if op == Operation.INSTALL:
        return (
            install_new,
            {
                "identity": window._identity,
                "opts": InstallOptions(
                    target_dir=selections.install_dir,
                    create_desktop_shortcut=selections.shortcut_desktop,
                    create_start_menu_shortcut=selections.shortcut_start_menu,
                    start_on_signin=selections.start_on_signin,
                ),
            },
        )

    if op in {Operation.UPGRADE, Operation.REINSTALL}:
        if current_install_dir is None:
            raise InstallerOperationError("No existing installation detected")
        return (
            upgrade_or_reinstall,
            {
                "identity": window._identity,
                "current_install_dir": current_install_dir,
                "opts": InstallOptions(
                    target_dir=selections.install_dir,
                    create_desktop_shortcut=selections.shortcut_desktop,
                    create_start_menu_shortcut=selections.shortcut_start_menu,
                    start_on_signin=selections.start_on_signin,
                ),
            },
        )

    if op == Operation.REPAIR:
        return (
            repair,
            {
                "identity": window._identity,
                "opts": RepairOptions(
                    restore_desktop_shortcut=selections.shortcut_desktop,
                    restore_start_menu_shortcut=selections.shortcut_start_menu,
                    restore_start_on_signin=selections.start_on_signin,
                ),
            },
        )

    if op == Operation.UNINSTALL:
        return (
            uninstall_with_feedback,
            {
                "identity": window._identity,
                "opts": UninstallOptions(remove_user_data=True),
            },
        )

    raise InstallerOperationError(f"Unsupported operation: {op}")
