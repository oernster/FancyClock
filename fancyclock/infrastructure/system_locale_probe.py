"""Host-system implementation of the SystemLocaleProbe port."""

from __future__ import annotations

import locale
import os
from typing import Callable, Mapping

LOCALE_ENV_VARS: tuple[str, ...] = ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE")
ENV_LIST_SEPARATOR = ":"


def _default_locale_getter() -> str | None:
    """Return the process locale language code, or ``None``."""
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
        except Exception:
            from_locale = None
        if from_locale:
            found.append(from_locale)

        for env_var in LOCALE_ENV_VARS:
            value = self._env.get(env_var)
            if value:
                found.append(value.split(ENV_LIST_SEPARATOR)[0])

        return tuple(found)
