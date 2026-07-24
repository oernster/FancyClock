"""FancyClock application package.

The package exports only the application entry point. ``main`` is resolved
lazily so importing subpackages (for example in tests) does not pull in Qt.
"""

from __future__ import annotations

__all__ = ["main"]


def __getattr__(name: str):
    if name == "main":
        from fancyclock.main import main

        return main
    raise AttributeError(name)
