"""In-app update check presentation: triggers, prompt and manual path.

The conclusion arrives from the application layer's ``UpdateService``; this
module only decides when to ask and how to present the answer. The HTTP
call runs on a worker thread and the result crosses back to the UI thread
through a Signal connected to a bound method of a UI-thread QObject, so the
delivery is a queued connection and every widget is touched where Qt
requires it.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from fancyclock.application.update import UpdateService, UpdateStatus

LAUNCH_CHECK_DELAY_MS = 3000
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60
SECONDS_PER_MINUTE = 60
MS_PER_SECOND = 1000
RECHECK_INTERVAL_MS = (
    HOURS_PER_DAY * MINUTES_PER_HOUR * SECONDS_PER_MINUTE * MS_PER_SECOND
)

TITLE_KEY = "update_available_title"
TEXT_KEY = "update_available_text"
DOWNLOAD_KEY = "update_download"
SKIP_KEY = "update_skip"
LATER_KEY = "update_later"
UP_TO_DATE_KEY = "update_up_to_date"
CHECK_FAILED_KEY = "update_check_failed"
MENU_KEY = "check_for_updates"


class UpdateCheckController(QObject):
    """Runs the update check off the UI thread and presents the outcome."""

    _result_ready = Signal(object, bool)

    def __init__(self, window, service: UpdateService) -> None:
        super().__init__(window)
        self._window = window
        self._service = service
        self._result_ready.connect(self._present_result)
        QTimer.singleShot(LAUNCH_CHECK_DELAY_MS, self.check_automatically)
        self._recheck_timer = QTimer(self)
        self._recheck_timer.setInterval(RECHECK_INTERVAL_MS)
        self._recheck_timer.timeout.connect(self.check_automatically)
        self._recheck_timer.start()

    def check_automatically(self) -> None:
        """Run a check that honours the skip and stays silent on failure."""
        self._start_worker(manual=False)

    def check_manually(self) -> None:
        """Run a check that ignores the skip and reports every outcome."""
        self._start_worker(manual=True)

    def _start_worker(self, manual: bool) -> None:
        skipped = None
        if not manual:
            skipped = self._window.settings.skipped_update_version()

        def run() -> None:
            try:
                status = self._service.check(skipped)
            except Exception:  # noqa: BLE001 (any error reads as unreachable)
                status = None
            self._result_ready.emit(status, manual)

        threading.Thread(target=run, daemon=True).start()

    def _translate(self, key: str) -> str:
        return self._window.i18n_manager.get_translation(key)

    def _present_result(self, status: UpdateStatus | None, manual: bool) -> None:
        if status is None:
            if manual:
                QMessageBox.information(
                    self._window,
                    self._translate(MENU_KEY),
                    self._translate(CHECK_FAILED_KEY),
                )
            return
        if status.update_available:
            self._prompt(status)
            return
        if manual:
            QMessageBox.information(
                self._window,
                self._translate(MENU_KEY),
                self._translate(UP_TO_DATE_KEY),
            )

    def _prompt(self, status: UpdateStatus) -> None:
        box = QMessageBox(self._window)
        box.setWindowTitle(self._translate(TITLE_KEY))
        box.setText(
            self._translate(TEXT_KEY).format(
                latest=status.latest, current=status.current
            )
        )
        download = box.addButton(self._translate(DOWNLOAD_KEY), QMessageBox.AcceptRole)
        skip = box.addButton(self._translate(SKIP_KEY), QMessageBox.DestructiveRole)
        box.addButton(self._translate(LATER_KEY), QMessageBox.RejectRole)
        box.setDefaultButton(download)
        box.exec()
        clicked = box.clickedButton()
        if clicked is download:
            url = status.download_url or status.page_url
            if url:
                QDesktopServices.openUrl(QUrl(url))
        elif clicked is skip and status.latest:
            self._window.settings.set_skipped_update_version(status.latest)
