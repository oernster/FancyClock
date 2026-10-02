"""Qt fixtures for the UI tests: one real QApplication, offscreen."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Return the one QApplication every UI test shares."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def close_orphaned_windows(qapp: QApplication):
    """Close and delete every top-level widget a test leaves behind."""
    yield
    for widget in qapp.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    qapp.processEvents()
