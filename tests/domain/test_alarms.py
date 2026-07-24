"""Tests for the alarm domain model."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from fancyclock.domain.alarms import (
    ALARM_COLORS,
    DEFAULT_COLOR,
    DEFAULT_SNOOZE_MINUTES,
    DEFAULT_SOUND,
    MONDAY,
    TUESDAY,
    Alarm,
    AlarmsState,
    AlarmValidationError,
    SnoozeState,
    color_hex,
)


def make_alarm(**overrides) -> Alarm:
    base = dict(
        alarm_id="a1",
        label="Work",
        hour=7,
        minute=30,
        weekdays=(MONDAY,),
        one_off_date=None,
        tz_id="Europe/London",
        color=DEFAULT_COLOR,
        sound=DEFAULT_SOUND,
        snooze_minutes=DEFAULT_SNOOZE_MINUTES,
        snooze_limit=None,
        enabled=True,
    )
    base.update(overrides)
    return Alarm(**base)


def make_snooze(**overrides) -> SnoozeState:
    base = dict(
        alarm_id="a1",
        snoozed_until_utc=datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc),
        snoozes_used=1,
        last_snooze_minutes=10,
    )
    base.update(overrides)
    return SnoozeState(**base)


def test_valid_repeating_alarm_constructs() -> None:
    alarm = make_alarm()
    assert alarm.is_repeating


def test_valid_one_off_alarm_constructs() -> None:
    alarm = make_alarm(weekdays=(), one_off_date=date(2026, 8, 1))
    assert not alarm.is_repeating


@pytest.mark.parametrize(
    "overrides",
    [
        {"alarm_id": ""},
        {"hour": -1},
        {"hour": 24},
        {"minute": -1},
        {"minute": 60},
        {"weekdays": (), "one_off_date": None},
        {"weekdays": (MONDAY,), "one_off_date": date(2026, 8, 1)},
        {"weekdays": (TUESDAY, MONDAY)},
        {"weekdays": (MONDAY, MONDAY)},
        {"weekdays": (7,)},
        {"tz_id": ""},
        {"color": "mauve"},
        {"sound": "kazoo"},
        {"snooze_minutes": 0},
        {"snooze_limit": 0},
    ],
)
def test_invalid_alarm_raises(overrides: dict) -> None:
    with pytest.raises(AlarmValidationError):
        make_alarm(**overrides)


def test_valid_snooze_state_constructs() -> None:
    state = make_snooze()
    assert state.snoozes_used == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"alarm_id": ""},
        {"snoozed_until_utc": datetime(2026, 7, 1, 8, 0)},
        {"snoozes_used": 0},
        {"last_snooze_minutes": 0},
    ],
)
def test_invalid_snooze_state_raises(overrides: dict) -> None:
    with pytest.raises(AlarmValidationError):
        make_snooze(**overrides)


def test_color_hex_returns_palette_value() -> None:
    name, value = ALARM_COLORS[2]
    assert color_hex(name) == value


def test_color_hex_falls_back_to_first_colour() -> None:
    assert color_hex("nonsense") == ALARM_COLORS[0][1]


def test_empty_state_has_master_on_and_no_alarms() -> None:
    state = AlarmsState.empty()
    assert state.master_enabled
    assert state.alarms == ()
    assert state.snooze_states == ()
    assert state.last_evaluated_utc is None


def test_alarm_by_id_finds_and_misses() -> None:
    alarm = make_alarm()
    state = AlarmsState(
        alarms=(alarm,),
        snooze_states=(),
        master_enabled=True,
        last_evaluated_utc=None,
    )
    assert state.alarm_by_id("a1") is alarm
    assert state.alarm_by_id("missing") is None


def test_snooze_for_finds_and_misses() -> None:
    snooze = make_snooze()
    state = AlarmsState(
        alarms=(),
        snooze_states=(snooze,),
        master_enabled=True,
        last_evaluated_utc=None,
    )
    assert state.snooze_for("a1") is snooze
    assert state.snooze_for("missing") is None
