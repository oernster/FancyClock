"""Alarm domain model: value objects, canonical presets and validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6
ALL_WEEKDAYS = (MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY)

HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60

ALARM_COLORS = (
    ("red", "#E11D2E"),
    ("amber", "#F59E0B"),
    ("green", "#22C55E"),
    ("teal", "#14B8A6"),
    ("blue", "#3B82F6"),
    ("violet", "#8B5CF6"),
    ("pink", "#EC4899"),
    ("slate", "#94A3B8"),
)
ALARM_COLOR_NAMES = tuple(name for name, _ in ALARM_COLORS)

SOUND_NAMES = ("beep", "chime", "bell", "pulse", "marimba")

SNOOZE_PRESET_MINUTES = (5, 10, 15, 30, 60, 120, 360, 720, 1440)
SNOOZE_LIMIT_PRESETS: tuple[int | None, ...] = (1, 3, 5, None)

DEFAULT_COLOR = "amber"
DEFAULT_SOUND = "chime"
DEFAULT_SNOOZE_MINUTES = 10
DEFAULT_SNOOZE_LIMIT: int | None = None


class AlarmError(ValueError):
    """Base class for alarm domain errors."""


class AlarmValidationError(AlarmError):
    """An alarm value object was constructed with invalid data."""


class AlarmImportError(AlarmError):
    """An alarm import document could not be read or validated."""


def color_hex(name: str) -> str:
    """Return the hex value of a palette colour, defaulting to the first."""
    for color_name, value in ALARM_COLORS:
        if color_name == name:
            return value
    return ALARM_COLORS[0][1]


@dataclass(frozen=True, slots=True)
class Alarm:
    """A configured alarm: either weekly-repeating or a one-off date."""

    alarm_id: str
    label: str
    hour: int
    minute: int
    weekdays: tuple[int, ...]
    one_off_date: date | None
    tz_id: str
    color: str
    sound: str
    snooze_minutes: int
    snooze_limit: int | None
    enabled: bool

    def __post_init__(self) -> None:
        if not self.alarm_id:
            raise AlarmValidationError("alarm_id must be non-empty")
        if not 0 <= self.hour < HOURS_PER_DAY:
            raise AlarmValidationError(f"hour {self.hour} out of range")
        if not 0 <= self.minute < MINUTES_PER_HOUR:
            raise AlarmValidationError(f"minute {self.minute} out of range")
        if bool(self.weekdays) == (self.one_off_date is not None):
            raise AlarmValidationError(
                "exactly one of weekdays or one_off_date must be set"
            )
        if tuple(sorted(set(self.weekdays))) != self.weekdays:
            raise AlarmValidationError("weekdays must be sorted and unique")
        for day in self.weekdays:
            if day not in ALL_WEEKDAYS:
                raise AlarmValidationError(f"weekday {day} out of range")
        if not self.tz_id:
            raise AlarmValidationError("tz_id must be non-empty")
        if self.color not in ALARM_COLOR_NAMES:
            raise AlarmValidationError(f"unknown colour {self.color!r}")
        if self.sound not in SOUND_NAMES:
            raise AlarmValidationError(f"unknown sound {self.sound!r}")
        if self.snooze_minutes <= 0:
            raise AlarmValidationError("snooze_minutes must be positive")
        if self.snooze_limit is not None and self.snooze_limit <= 0:
            raise AlarmValidationError("snooze_limit must be positive or None")

    @property
    def is_repeating(self) -> bool:
        """Return True when the alarm repeats on weekdays."""
        return bool(self.weekdays)


@dataclass(frozen=True, slots=True)
class SnoozeState:
    """The live snooze episode of one alarm; survives restarts."""

    alarm_id: str
    snoozed_until_utc: datetime
    snoozes_used: int
    last_snooze_minutes: int

    def __post_init__(self) -> None:
        if not self.alarm_id:
            raise AlarmValidationError("alarm_id must be non-empty")
        if self.snoozed_until_utc.tzinfo is None:
            raise AlarmValidationError("snoozed_until_utc must be aware")
        if self.snoozes_used < 1:
            raise AlarmValidationError("snoozes_used must be at least 1")
        if self.last_snooze_minutes <= 0:
            raise AlarmValidationError("last_snooze_minutes must be positive")


@dataclass(frozen=True, slots=True)
class AlarmsState:
    """The whole persisted alarm document."""

    alarms: tuple[Alarm, ...]
    snooze_states: tuple[SnoozeState, ...]
    master_enabled: bool
    last_evaluated_utc: datetime | None

    @classmethod
    def empty(cls) -> AlarmsState:
        """Return the state of a fresh install: no alarms, master on."""
        return cls(
            alarms=(),
            snooze_states=(),
            master_enabled=True,
            last_evaluated_utc=None,
        )

    def alarm_by_id(self, alarm_id: str) -> Alarm | None:
        """Return the alarm with ``alarm_id``, or ``None``."""
        for alarm in self.alarms:
            if alarm.alarm_id == alarm_id:
                return alarm
        return None

    def snooze_for(self, alarm_id: str) -> SnoozeState | None:
        """Return the live snooze state for ``alarm_id``, or ``None``."""
        for state in self.snooze_states:
            if state.alarm_id == alarm_id:
                return state
        return None
