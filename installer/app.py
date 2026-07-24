"""FancyClock installer GUI entrypoint."""

from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication

from fancyclock.version import APP_DISPLAY_NAME, __version__
from installer.cli import parse_args, wants_remove_user_data
from installer.shared.logging_setup import setup_installer_logging
from installer.ui.icons import (
    build_installer_window_icon,
    set_windows_app_user_model_id,
)
from installer.ui.main_window import InstallerMainWindow

INSTALLER_APPUSERMODELID = "FancyClock.Installer"


def main(argv: list[str] | None = None) -> int:
    if os.name != "nt":
        print("Fancy Clock installer is Windows-only")
        return 2

    log_path = setup_installer_logging()

    def _excepthook(exc_type, exc, tb):  # noqa: ANN001
        # Ensure we capture crashes that happen on the main thread.
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n=== Unhandled exception ===\n")
            traceback.print_exception(exc_type, exc, tb, file=f)
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _excepthook

    args = parse_args(list(argv) if argv is not None else sys.argv[1:])

    # When invoked as uninstaller from Settings, we can optionally run without UI
    # in the future. For now, always show UI.
    _ = wants_remove_user_data(args)

    app = QApplication([f"{APP_DISPLAY_NAME} Setup"])
    app.setApplicationName(f"{APP_DISPLAY_NAME} Setup")
    app.setApplicationVersion(__version__)

    # Best-effort: ensure correct Windows taskbar grouping/icon.
    set_windows_app_user_model_id(INSTALLER_APPUSERMODELID)

    # Set the application icon as early as possible so Windows uses it for the
    # taskbar and titlebar.
    logger = logging.getLogger("installer.icon")
    try:
        icon = build_installer_window_icon(
            project_root=Path(__file__).resolve().parents[2]
        )
        if not icon.isNull():
            app.setWindowIcon(icon)
            logger.info("Installer window icon applied (QApplication).")
    except Exception:
        logger.exception("Failed to set QApplication window icon")

    win = InstallerMainWindow(cli_args=args)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
