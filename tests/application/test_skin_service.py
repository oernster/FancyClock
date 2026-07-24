"""SkinService tests using a hand-written fake media library."""

from __future__ import annotations

from fancyclock.application.skins import SkinEntry, SkinService

FAKE_FILES = (
    "C:\\media\\koi_carp.mp4",
    "C:\\media\\spinning_galaxy.mp4",
)


class FakeMediaLibrary:
    def skin_files(self) -> tuple[str, ...]:
        return FAKE_FILES


def test_entries_have_display_names_and_paths() -> None:
    service = SkinService(media=FakeMediaLibrary())
    assert service.entries() == (
        SkinEntry(display_name="Koi Carp", path=FAKE_FILES[0]),
        SkinEntry(display_name="Spinning Galaxy", path=FAKE_FILES[1]),
    )


def test_find_by_stem_is_case_insensitive() -> None:
    service = SkinService(media=FakeMediaLibrary())
    assert service.find_by_stem("KOI_CARP") == FAKE_FILES[0]
    assert service.find_by_stem("spinning_galaxy") == FAKE_FILES[1]
    assert service.find_by_stem("missing") is None
