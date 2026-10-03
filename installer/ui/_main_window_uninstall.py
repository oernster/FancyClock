from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from fancyclock.version import APP_DISPLAY_NAME
from installer.cli import wants_remove_user_data
from installer.state.model import Operation

if TYPE_CHECKING:  # pragma: no cover
    from installer.ui.main_window import InstallerMainWindow


def confirmation_text(*, remove_user_data: bool) -> str:
    """Say what the uninstall will do, including what happens to user data."""

    if remove_user_data:
        return (
            f"This will uninstall {APP_DISPLAY_NAME} for the current user and "
            "remove user data and cache."
        )
    return (
        f"This will uninstall {APP_DISPLAY_NAME} for the current user and "
        "keep your user data and cache."
    )


def confirm_and_run_uninstall(window: InstallerMainWindow) -> None:
    box = QMessageBox(window)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Confirm uninstall")
    box.setText(
        confirmation_text(remove_user_data=wants_remove_user_data(window._cli_args))
    )
    uninstall_btn = box.addButton("Uninstall", QMessageBox.AcceptRole)
    box.addButton("Cancel", QMessageBox.RejectRole)
    box.exec()
    if box.clickedButton() == uninstall_btn:
        window._request_operation(Operation.UNINSTALL)
