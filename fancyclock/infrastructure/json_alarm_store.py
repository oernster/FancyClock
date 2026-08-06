"""JSON persistence for alarms: the store and the import/export porter.

The store is tolerant on load (a corrupt document or entry never crashes
the app; bad entries are skipped). The porter is strict on import and
raises ``AlarmImportError`` so the user learns their file is bad.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fancyclock.application.ports import AlarmLoad
from fancyclock.domain.alarms import (
    Alarm,
    AlarmError,
    AlarmImportError,
    AlarmsState,
    SnoozeState,
)
from fancyclock.infrastructure.json_settings_store import default_config_dir

ALARMS_FILE_NAME = "alarms.json"
DOCUMENT_VERSION = 1

# Reported when the document itself could not be read, so the count stands for
# "the file", not for a number of entries: nothing inside it could be counted.
_WHOLE_FILE = 1


def _alarm_to_dict(alarm: Alarm) -> dict[str, Any]:
    return {
        "id": alarm.alarm_id,
        "label": alarm.label,
        "hour": alarm.hour,
        "minute": alarm.minute,
        "weekdays": list(alarm.weekdays),
        "date": alarm.one_off_date.isoformat() if alarm.one_off_date else None,
        "tz": alarm.tz_id,
        "color": alarm.color,
        "sound": alarm.sound,
        "snooze_minutes": alarm.snooze_minutes,
        "snooze_limit": alarm.snooze_limit,
        "enabled": alarm.enabled,
    }


def _alarm_from_dict(data: dict[str, Any]) -> Alarm:
    raw_date = data.get("date")
    return Alarm(
        alarm_id=str(data["id"]),
        label=str(data.get("label", "")),
        hour=int(data["hour"]),
        minute=int(data["minute"]),
        weekdays=tuple(int(day) for day in data.get("weekdays", ())),
        one_off_date=date.fromisoformat(raw_date) if raw_date else None,
        tz_id=str(data["tz"]),
        color=str(data["color"]),
        sound=str(data["sound"]),
        snooze_minutes=int(data["snooze_minutes"]),
        snooze_limit=(
            int(data["snooze_limit"]) if data.get("snooze_limit") is not None else None
        ),
        enabled=bool(data.get("enabled", True)),
    )


def _snooze_to_dict(state: SnoozeState) -> dict[str, Any]:
    return {
        "id": state.alarm_id,
        "until": state.snoozed_until_utc.isoformat(),
        "used": state.snoozes_used,
        "last_minutes": state.last_snooze_minutes,
    }


def _snooze_from_dict(data: dict[str, Any]) -> SnoozeState:
    return SnoozeState(
        alarm_id=str(data["id"]),
        snoozed_until_utc=datetime.fromisoformat(str(data["until"])),
        snoozes_used=int(data["used"]),
        last_snooze_minutes=int(data["last_minutes"]),
    )


class JsonAlarmStore:
    """Persists the alarm document with an atomic temp-file swap."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir if config_dir else default_config_dir()

    def alarms_path(self) -> Path:
        """Return the alarms file path, creating the directory if needed."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        return self._config_dir / ALARMS_FILE_NAME

    def load(self) -> AlarmLoad:
        """Return the persisted state; tolerant of missing or bad data.

        Every tolerated failure is counted rather than merely survived. The
        caller is told how many entries were unreadable so it can say so once,
        because an alarm silently dropped from the list is an alarm that will
        not ring at the time the user set.
        """
        path = self.alarms_path()
        if not path.exists():
            # No file yet: a first run, not damage. Nothing was lost.
            return AlarmLoad(state=AlarmsState.empty())
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:  # noqa: BLE001
            # Unreadable or not valid JSON. Falls back to an empty document so
            # the clock still starts. The whole file is reported lost.
            return AlarmLoad(state=AlarmsState.empty(), skipped_alarms=_WHOLE_FILE)
        if not isinstance(data, dict):
            # Valid JSON of the wrong shape (a list or a scalar). Same
            # fallback: an empty document, with the whole file reported lost.
            return AlarmLoad(state=AlarmsState.empty(), skipped_alarms=_WHOLE_FILE)

        alarms: list[Alarm] = []
        skipped_alarms = 0
        for entry in data.get("alarms", ()):
            try:
                alarms.append(_alarm_from_dict(entry))
            except Exception:  # noqa: BLE001
                # One malformed alarm entry: falls back to skipping that entry
                # alone, so the remaining alarms still load. Counted, because
                # this is the alarm that will not ring.
                skipped_alarms += 1
        known = {alarm.alarm_id for alarm in alarms}
        snoozes: list[SnoozeState] = []
        skipped_snoozes = 0
        for entry in data.get("snooze_states", ()):
            try:
                state = _snooze_from_dict(entry)
            except Exception:  # noqa: BLE001
                # One malformed snooze record: falls back to skipping it, which
                # loses only the snooze, never the alarm behind it. Counted so
                # the total is honest, though it matters less than an alarm.
                skipped_snoozes += 1
                continue
            if state.alarm_id in known:
                snoozes.append(state)

        raw_watermark = data.get("last_evaluated_utc")
        try:
            watermark = datetime.fromisoformat(raw_watermark) if raw_watermark else None
        except Exception:  # noqa: BLE001
            # An unparseable watermark falls back to None, which makes the next
            # tick treat the session as fresh. Not counted: no alarm is lost.
            watermark = None

        return AlarmLoad(
            state=AlarmsState(
                alarms=tuple(alarms),
                snooze_states=tuple(snoozes),
                master_enabled=data.get("master_enabled", True) is not False,
                last_evaluated_utc=watermark,
            ),
            skipped_alarms=skipped_alarms,
            skipped_snoozes=skipped_snoozes,
        )

    def save(self, state: AlarmsState) -> None:
        """Persist ``state`` atomically."""
        document = {
            "version": DOCUMENT_VERSION,
            "master_enabled": state.master_enabled,
            "last_evaluated_utc": (
                state.last_evaluated_utc.isoformat()
                if state.last_evaluated_utc
                else None
            ),
            "alarms": [_alarm_to_dict(alarm) for alarm in state.alarms],
            "snooze_states": [
                _snooze_to_dict(snooze) for snooze in state.snooze_states
            ],
        }
        path = self.alarms_path()
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(document, f, indent=2, sort_keys=True)
        tmp.replace(path)


class JsonAlarmPorter:
    """Imports and exports alarms as a versioned JSON document."""

    def export_alarms(self, path: Path, alarms: tuple[Alarm, ...]) -> None:
        """Write ``alarms`` to ``path`` as a version 1 document."""
        document = {
            "version": DOCUMENT_VERSION,
            "alarms": [_alarm_to_dict(alarm) for alarm in alarms],
        }
        with Path(path).open("w", encoding="utf-8") as f:
            json.dump(document, f, indent=2, sort_keys=True)

    def import_alarms(self, path: Path) -> tuple[Alarm, ...]:
        """Read alarms from ``path``; raises ``AlarmImportError`` on bad data."""
        try:
            with Path(path).open("r", encoding="utf-8") as f:
                data = json.load(f)
        except OSError as error:
            raise AlarmImportError(f"cannot read {path}: {error}") from error
        except ValueError as error:
            raise AlarmImportError(f"{path} is not valid JSON") from error
        if not isinstance(data, dict):
            raise AlarmImportError(f"{path} is not an alarm document")
        if data.get("version") != DOCUMENT_VERSION:
            raise AlarmImportError(
                f"unsupported alarm document version {data.get('version')!r}"
            )
        entries = data.get("alarms")
        if not isinstance(entries, list):
            raise AlarmImportError(f"{path} has no alarm list")
        alarms: list[Alarm] = []
        for entry in entries:
            try:
                alarms.append(_alarm_from_dict(entry))
            except AlarmError:
                raise
            except Exception as error:
                raise AlarmImportError(f"bad alarm entry: {error}") from error
        return tuple(alarms)
