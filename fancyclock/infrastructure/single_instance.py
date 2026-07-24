from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceGuard(QObject):
    """
    RAII-style single-instance guard using QLocalServer / QLocalSocket.

    Usage in main.py:

        guard = SingleInstanceGuard("uk.codecrafter.FancyClock.singleton")
        if not guard.acquire():
            guard.notify_existing_instance()
            return 0

        app.single_instance_guard = guard
        window = ClockWindow()
        guard.activated.connect(window.bring_to_front)
        window.show()

    Semantics:
    - Only the process that successfully listens on the name is "primary".
    - Secondary instances connect to that name, notify it, then exit.
    """

    activated = Signal()  # emitted in primary when a secondary connects

    def __init__(self, server_name: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server_name = server_name
        self._server: QLocalServer | None = None
        self._is_primary: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self) -> bool:
        """
        Try to become the primary instance.

        Returns True if this process is the primary instance,
        False if another instance is already running.
        """

        # 1) Try to connect to an existing server first.
        #    If this succeeds, another instance is already running.
        probe = QLocalSocket(self)
        probe.connectToServer(self._server_name)
        if probe.waitForConnected(100):
            probe.disconnectFromServer()
            probe.deleteLater()
            self._server = None
            self._is_primary = False
            return False

        probe.abort()
        probe.deleteLater()

        # 2) No live server was found; remove any stale socket and try to listen.
        QLocalServer.removeServer(self._server_name)

        server = QLocalServer(self)
        if not server.listen(self._server_name):
            # Could not listen for some reason; behave as "not primary"
            self._server = None
            self._is_primary = False
            return False

        server.newConnection.connect(self._on_new_connection)
        self._server = server
        self._is_primary = True
        return True

    def notify_existing_instance(self) -> None:
        """
        Called from a *secondary* instance when acquire() returned False.

        Attempts to connect to the primary instance and send a small
        'activate' ping so that it can bring its window to the front.
        """

        socket = QLocalSocket(self)
        socket.connectToServer(self._server_name)

        if not socket.waitForConnected(500):
            socket.abort()
            socket.deleteLater()
            return

        socket.write(b"activate")
        socket.flush()
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        socket.deleteLater()

    @property
    def is_primary(self) -> bool:
        return self._is_primary

    # ------------------------------------------------------------------
    # Internal slot
    # ------------------------------------------------------------------

    def _on_new_connection(self) -> None:
        """
        Invoked in the primary instance when a secondary instance connects.
        Consumes and closes the connection, then emits `activated`.
        """
        if not self._server:
            return

        socket = self._server.nextPendingConnection()
        if socket is None:
            return

        socket.readAll()
        socket.disconnectFromServer()
        socket.deleteLater()

        self.activated.emit()

    # Optional sugar if you ever want `with SingleInstanceGuard(...) as guard:`
    def __enter__(self) -> "SingleInstanceGuard":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # QLocalServer is owned by this QObject and cleaned up automatically.
        pass
