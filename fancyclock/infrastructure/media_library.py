"""Filesystem implementation of the MediaLibrary port."""

from __future__ import annotations

from pathlib import Path

from fancyclock.domain.skins import is_skin_filename


class FilesystemMediaLibrary:
    """Enumerates video skin files from the bundled media directory."""

    def __init__(self, media_dir: Path) -> None:
        self._media_dir = media_dir

    def skin_files(self) -> tuple[str, ...]:
        """Return absolute paths of the available skin files, sorted."""
        if not self._media_dir.is_dir():
            return ()
        return tuple(
            str(path)
            for path in sorted(self._media_dir.iterdir())
            if is_skin_filename(path.name)
        )
