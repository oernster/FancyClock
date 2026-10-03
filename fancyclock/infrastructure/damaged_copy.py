"""Keep a damaged data file aside before anything saves over it.

A tolerant load reads what it can and the next save writes only that, which
replaces the damaged file for good. Copying it aside first leaves what could
not be read on disk for a hand repair. Each damage gets its own numbered copy,
so a later one never replaces an earlier one.
"""

from __future__ import annotations

from itertools import count
from pathlib import Path
from typing import Callable

DAMAGED_MARKER = "damaged"
FIRST_COPY_NUMBER = 1

CopyFile = Callable[[Path, Path], object]


def damaged_copy_target(path: Path) -> Path:
    """Return the first free ``<stem>.damaged-<n><suffix>`` beside ``path``."""
    numbers = count(FIRST_COPY_NUMBER)
    target = _numbered(path, next(numbers))
    while target.exists():
        target = _numbered(path, next(numbers))
    return target


def _numbered(path: Path, number: int) -> Path:
    return path.with_name(f"{path.stem}.{DAMAGED_MARKER}-{number}{path.suffix}")


def keep_aside(path: Path, copy_file: CopyFile) -> Path | None:
    """Copy ``path`` to a fresh damaged-copy name; ``None`` if it failed."""
    target = damaged_copy_target(path)
    try:
        copy_file(path, target)
    except OSError:
        return None
    return target
