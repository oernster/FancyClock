"""Video skin discovery service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from fancyclock.application.ports import MediaLibrary
from fancyclock.domain.skins import skin_display_name, skin_stem


@dataclass(frozen=True, slots=True)
class SkinEntry:
    """One selectable video skin."""

    display_name: str
    path: str


class SkinService:
    """Lists the available skins and resolves them by name."""

    def __init__(self, media: MediaLibrary) -> None:
        self._media = media

    def entries(self) -> tuple[SkinEntry, ...]:
        """Return the available skins in filename order."""
        return tuple(
            SkinEntry(
                display_name=skin_display_name(PurePath(path).name),
                path=path,
            )
            for path in self._media.skin_files()
        )

    def find_by_stem(self, name: str) -> str | None:
        """Return the path of the skin whose stem matches ``name``."""
        wanted = name.lower()
        for path in self._media.skin_files():
            if skin_stem(PurePath(path).name).lower() == wanted:
                return path
        return None
