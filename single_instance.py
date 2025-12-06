# single_instance.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6 import QtCore


@dataclass
class SingleInstanceGuard:
    """
    Cross-platform single-instance guard using QSystemSemaphore + QSharedMemory.

    Usage:
        guard = SingleInstanceGuard("FancyClockSingleton")
        if not guard.is_primary:
            # another instance is already running
            ...

    RAII-ish: as long as the object lives, the shared memory segment exists.
    When the process exits, the segment is detached.
    """

    key: str
    _semaphore: QtCore.QSystemSemaphore = None
    _memory: QtCore.QSharedMemory = None
    _is_primary: bool = False

    def __post_init__(self) -> None:
        # A separate key for the semaphore avoids clashes with the shared memory key.
        sem_key = f"{self.key}_sem"

        self._semaphore = QtCore.QSystemSemaphore(sem_key, 1)
        self._memory = QtCore.QSharedMemory(self.key)

        self._acquire()

    def _acquire(self) -> None:
        # Serialize operations on the shared memory
        self._semaphore.acquire()
        try:
            # If a segment already exists and we can attach, another instance is running.
            if self._memory.attach():
                # We immediately detach again; we only needed to check existence.
                self._memory.detach()
                self._is_primary = False
                return

            # No existing segment – create one byte just to mark presence.
            if not self._memory.create(1):
                # Could not create; treat as "another instance is running".
                self._is_primary = False
                return

            self._is_primary = True
        finally:
            self._semaphore.release()

    @property
    def is_primary(self) -> bool:
        """True if this process is the first (and owning) instance."""
        return self._is_primary

    def release(self) -> None:
        """Explicitly release the shared memory segment."""
        if not self._is_primary:
            return

        self._semaphore.acquire()
        try:
            if self._memory.isAttached():
                self._memory.detach()
        finally:
            self._semaphore.release()
        self._is_primary = False

    # Context-manager support (RAII style)
    def __enter__(self) -> "SingleInstanceGuard":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    def __del__(self) -> None:
        # Best-effort cleanup; Python does not guarantee destructor timing,
        # but on normal exit this will run.
        try:
            self.release()
        except Exception:
            pass
