"""FilesystemMediaLibrary tests against a real temp directory."""

from __future__ import annotations

from fancyclock.infrastructure.media_library import FilesystemMediaLibrary


def test_lists_only_skin_files_sorted(tmp_path) -> None:
    (tmp_path / "waves.mp4").write_bytes(b"")
    (tmp_path / "KOI.MP4").write_bytes(b"")
    (tmp_path / "notes.txt").write_bytes(b"")

    library = FilesystemMediaLibrary(tmp_path)
    files = library.skin_files()

    assert [f.split("\\")[-1].split("/")[-1] for f in files] == [
        "KOI.MP4",
        "waves.mp4",
    ]


def test_missing_directory_yields_empty(tmp_path) -> None:
    library = FilesystemMediaLibrary(tmp_path / "absent")
    assert library.skin_files() == ()
