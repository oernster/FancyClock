"""Application entrypoint.

Kept small so `main.py` can remain a thin wrapper.
"""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QCoreApplication, QLoggingCategory
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from fancyclock.window import ClockWindow
from single_instance import SingleInstanceGuard


def main() -> int:
    """Run the FancyClock Qt application."""
    QLoggingCategory.setFilterRules(
        "qt.text.font.db=false\n"
        "qt.multimedia.ffmpeg=false\n"
        "qt.multimedia.ffmpeg.*=false\n"
    )

    if sys.platform == "win32":
        try:
            myappid = "uk.codecrafter.FancyClock"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    QGuiApplication.setDesktopFileName("uk.codecrafter.FancyClock")
    app = QApplication(sys.argv)

    QCoreApplication.setOrganizationName("OliverErnster")
    QCoreApplication.setApplicationName("FancyClock")

    guard = SingleInstanceGuard("uk.codecrafter.FancyClock.singleton")
    if not guard.acquire():
        guard.notify_existing_instance()
        return 0

    app.single_instance_guard = guard

    window = ClockWindow()
    guard.activated.connect(window.bring_to_front)

    window.show()
    return app.exec()
