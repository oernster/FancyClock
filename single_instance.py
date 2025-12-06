from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceGuard(QObject):
    """
    Cross-platform single-instance guard using QLocalServer/QLocalSocket.

    Usage in main.py:

        guard = SingleInstanceGuard("uk.codecrafter.FancyClock.singleton")

        if not guard.acquire():
            guard.notify_existing_instance()
            return 0

        guard.activated.connect(window.bring_to_front)
    """

    activated = Signal()  # emitted in the *primary* instance when a 2nd one starts

    def __init__(self, server_name: str, parent=None):
        super().__init__(parent)
        self._server_name = server_name
        self._server: QLocalServer | None = None
        self._is_primary = False

    # ------------------------------------------------------------------ #
    # Public API expected by main.py
    # ------------------------------------------------------------------ #

    def acquire(self) -> bool:
        """
        Try to become the primary (single) instance.

        Returns True in the first/primary process, False in later processes.
        """
        # Clean up any stale socket from a previous crash
        try:
            QLocalServer.removeServer(self._server_name)
        except Exception:
            pass

        server = QLocalServer(self)
        server.setSocketOptions(QLocalServer.WorldAccessOption)

        if not server.listen(self._server_name):
            # Another instance is already listening
            self._server = None
            self._is_primary = False
            return False

        server.newConnection.connect(self._on_new_connection)
        self._server = server
        self._is_primary = True
        return True

    def notify_existing_instance(self) -> None:
        """
        Called from a *secondary* instance to ping the primary one.

        The primary instance will receive a connection and emit `activated`.
        """
        socket = QLocalSocket()
        socket.connectToServer(self._server_name)

        if socket.waitForConnected(250):
            try:
                socket.write(b"activate")
                socket.flush()
                socket.waitForBytesWritten(250)
            except Exception:
                pass
            socket.disconnectFromServer()

        socket.close()

    # ------------------------------------------------------------------ #
    # Internal callbacks
    # ------------------------------------------------------------------ #

    def _on_new_connection(self) -> None:
        """
        Invoked in the primary instance when a secondary instance connects.
        """
        if not self._server:
            return

        socket = self._server.nextPendingConnection()
        if socket is not None:
            # We don't actually care about the payload; just close.
            socket.disconnectFromServer()
            socket.close()

        # Tell whoever is listening (main window) to bring itself to front
        self.activated.emit()
