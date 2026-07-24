"""Domain skin-naming tests."""

from __future__ import annotations

from fancyclock.domain.skins import (
    is_skin_filename,
    skin_display_name,
    skin_stem,
)


def test_is_skin_filename_case_insensitive() -> None:
    assert is_skin_filename("waves.mp4")
    assert is_skin_filename("WAVES.MP4")
    assert not is_skin_filename("notes.txt")


def test_skin_stem_strips_suffix() -> None:
    assert skin_stem("spinning_galaxy.mp4") == "spinning_galaxy"
    assert skin_stem("readme") == "readme"


def test_skin_display_name() -> None:
    assert skin_display_name("spinning_galaxy.mp4") == "Spinning Galaxy"
