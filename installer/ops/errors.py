"""Installer operation errors."""

from __future__ import annotations


class InstallerOperationError(RuntimeError):
    pass


class AppRunningError(InstallerOperationError):
    """Raised when FancyClock is running and the operation requires it be closed."""
