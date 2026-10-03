"""Host-system implementation of the SystemLocaleProbe port."""

from __future__ import annotations

import ctypes
import locale
import os
import sys
from typing import Any, Callable, Mapping

LOCALE_ENV_VARS: tuple[str, ...] = ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE")
ENV_LIST_SEPARATOR = ":"
WINDOWS_PLATFORM = "win32"
# LOCALE_NAME_MAX_LENGTH from winnls.h, counting the terminating null.
LOCALE_NAME_MAX_LENGTH = 85
API_FAILED = 0


def _windows_locale_name(kernel32: Any) -> str | None:
    """Return the user's BCP-47 locale name (``fr-FR``) from Windows.

    ``locale.getlocale()`` on Windows reports a display name such as
    ``French_France``, which names no locale code; this asks the API that
    reports the code itself.
    """
    buffer = ctypes.create_unicode_buffer(LOCALE_NAME_MAX_LENGTH)
    if kernel32.GetUserDefaultLocaleName(buffer, LOCALE_NAME_MAX_LENGTH) == API_FAILED:
        return None
    return buffer.value or None


def _read_windows_locale_name() -> str | None:
    """Ask the real kernel32 for the user's locale name."""
    return _windows_locale_name(ctypes.windll.kernel32)


def _default_locale_getter(
    platform: str = sys.platform,
    windows_reader: Callable[[], str | None] = _read_windows_locale_name,
) -> str | None:
    """Return the system locale code, else ``None``.

    Windows is asked for its BCP-47 name first. The process locale is used
    elsewhere, as it is when Windows gives no name.
    """
    if platform == WINDOWS_PLATFORM:
        name = windows_reader()
        if name:
            return name
    return locale.getlocale()[0]


class EnvironmentLocaleProbe:
    """Reads raw locale hints from the process locale and environment."""

    def __init__(
        self,
        env: Mapping[str, str] | None = None,
        locale_getter: Callable[[], str | None] = _default_locale_getter,
    ) -> None:
        self._env = env if env is not None else os.environ
        self._locale_getter = locale_getter

    def candidates(self) -> tuple[str, ...]:
        """Return raw locale strings in preference order."""
        found: list[str] = []

        try:
            from_locale = self._locale_getter()
        except Exception:  # noqa: BLE001
            # Falls back to no reading from the OS, leaving the environment
            # variables below as the source. The getter is platform code
            # whose failures differ per operating system.
            from_locale = None
        if from_locale:
            found.append(from_locale)

        for env_var in LOCALE_ENV_VARS:
            value = self._env.get(env_var)
            if value:
                found.append(value.split(ENV_LIST_SEPARATOR)[0])

        return tuple(found)
