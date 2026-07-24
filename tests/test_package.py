"""Package export tests."""

from __future__ import annotations

import pytest

import fancyclock


def test_main_is_exported_lazily() -> None:
    assert callable(fancyclock.main)
    assert fancyclock.__all__ == ["main"]


def test_unknown_attribute_raises() -> None:
    with pytest.raises(AttributeError):
        getattr(fancyclock, "no_such_attribute")
