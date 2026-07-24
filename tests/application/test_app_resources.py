"""ResourcePaths value-object tests."""

from __future__ import annotations

import dataclasses

import pytest

from fancyclock.application.resources import ResourcePaths


def test_resource_paths_is_frozen() -> None:
    paths = ResourcePaths(
        app_icon="assets/fancyclock.ico",
        about_icon_png="assets/fancyclock_icon_256.png",
        license_file=None,
    )
    assert paths.license_file is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        paths.app_icon = "other.ico"
