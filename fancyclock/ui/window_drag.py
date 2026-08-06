"""Clock window drag (mouse) behavior mixin."""

from __future__ import annotations

from PySide6.QtCore import Qt


class WindowDragMixin:
    """Enables click-and-drag to move the window."""

    def mousePressEvent(self, event):  # noqa: N802 (Qt override)
        if event.button() == Qt.LeftButton:
            try:
                self.old_pos = event.globalPosition().toPoint()
            except AttributeError:
                # Qt 5 has no globalPosition(); globalPos() is its
                # equivalent. Nothing else about a mouse press can fail
                # here, so nothing else is caught.
                self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):  # noqa: N802 (Qt override)
        if self.old_pos is not None and event.buttons() & Qt.LeftButton:
            try:
                new_pos = event.globalPosition().toPoint()
            except AttributeError:
                # The same Qt 5 fallback as the press handler above.
                new_pos = event.globalPos()
            delta = new_pos - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = new_pos

    def mouseReleaseEvent(self, event):  # noqa: N802 (Qt override)
        if event.button() == Qt.LeftButton:
            self.old_pos = None
