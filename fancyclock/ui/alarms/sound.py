"""Alarm sound playback over the bundled WAV set."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

SOUND_FILE_SUFFIX = ".wav"
SINGLE_PLAY_LOOPS = 1


class AlarmSoundPlayer(QObject):
    """Plays one alarm sound at a time, looping until stopped."""

    def __init__(self, sounds_dir: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._sounds_dir = Path(sounds_dir)
        self._effect: QSoundEffect | None = None

    def _source_for(self, sound_name: str) -> QUrl:
        path = self._sounds_dir / f"{sound_name}{SOUND_FILE_SUFFIX}"
        return QUrl.fromLocalFile(str(path))

    def _play(self, sound_name: str, volume: float, loops: int) -> None:
        self.stop()
        effect = QSoundEffect(self)
        effect.setSource(self._source_for(sound_name))
        effect.setLoopCount(loops)
        effect.setVolume(volume)
        effect.play()
        self._effect = effect

    def play_looping(self, sound_name: str, volume: float) -> None:
        """Play ``sound_name`` on an endless loop at ``volume`` (0 to 1)."""
        self._play(sound_name, volume, QSoundEffect.Loop.Infinite.value)

    def preview(self, sound_name: str, volume: float) -> None:
        """Play ``sound_name`` once at ``volume`` (0 to 1)."""
        self._play(sound_name, volume, SINGLE_PLAY_LOOPS)

    def stop(self) -> None:
        """Stop any current playback."""
        if self._effect is not None:
            self._effect.stop()
            self._effect.deleteLater()
            self._effect = None
