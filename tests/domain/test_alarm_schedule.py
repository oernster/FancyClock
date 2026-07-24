"""Tests for pure alarm scheduling: DST policy, occurrences, evaluation."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fancyclock.domain.alarm_schedule import (
    evaluate,
    next_occurrence,
    resolve_wall_time,
    upcoming_occurrence,
)
from fancyclock.domain.alarms import (
    ALL_WEEKDAYS,
    FRIDAY,
    MONDAY,
    AlarmsState,
    SnoozeState,
)
from tests.domain.test_alarms import make_alarm

LONDON = ZoneInfo("Europe/London")
UTC = timezone.utc


def resolve_tz(tz_id: str):
    return ZoneInfo(tz_id)


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def make_state(
    alarms=(),
    snooze_states=(),
    master_enabled=True,
    last_evaluated_utc=None,
) -> AlarmsState:
    return AlarmsState(
        alarms=tuple(alarms),
        snooze_states=tuple(snooze_states),
        master_enabled=master_enabled,
        last_evaluated_utc=last_evaluated_utc,
    )


# ---------------------------------------------------------------------------
# resolve_wall_time
# ---------------------------------------------------------------------------
def test_resolve_normal_summer_wall_time() -> None:
    instant = resolve_wall_time(datetime(2026, 7, 1, 7, 30), LONDON)
    assert instant == utc(2026, 7, 1, 6, 30)


def test_resolve_ambiguous_wall_time_takes_first_occurrence() -> None:
    # UK clocks fall back 2026-10-25 02:00 BST -> 01:00 GMT; 01:30 happens
    # twice and the first (BST, UTC+1) occurrence wins.
    instant = resolve_wall_time(datetime(2026, 10, 25, 1, 30), LONDON)
    assert instant == utc(2026, 10, 25, 0, 30)


def test_resolve_nonexistent_wall_time_steps_to_gap_end() -> None:
    # UK clocks spring forward 2026-03-29 01:00 GMT -> 02:00 BST; 01:30
    # never happens and fires at 02:00 BST, the first valid instant.
    instant = resolve_wall_time(datetime(2026, 3, 29, 1, 30), LONDON)
    assert instant == utc(2026, 3, 29, 1, 0)


# ---------------------------------------------------------------------------
# next_occurrence
# ---------------------------------------------------------------------------
def test_one_off_in_the_future_resolves() -> None:
    alarm = make_alarm(weekdays=(), one_off_date=date(2026, 8, 1), hour=9, minute=0)
    occurrence = next_occurrence(alarm, utc(2026, 7, 1, 12, 0), LONDON)
    assert occurrence == utc(2026, 8, 1, 8, 0)


def test_one_off_in_the_past_returns_none() -> None:
    alarm = make_alarm(weekdays=(), one_off_date=date(2026, 6, 1), hour=9, minute=0)
    assert next_occurrence(alarm, utc(2026, 7, 1, 12, 0), LONDON) is None


def test_repeating_skips_to_the_next_matching_weekday() -> None:
    # 2026-07-01 is a Wednesday; the next Monday is 2026-07-06.
    alarm = make_alarm(weekdays=(MONDAY,), hour=7, minute=30)
    occurrence = next_occurrence(alarm, utc(2026, 7, 1, 12, 0), LONDON)
    assert occurrence == utc(2026, 7, 6, 6, 30)


def test_repeating_fires_later_today_when_time_not_passed() -> None:
    # 2026-07-03 is a Friday; 07:30 BST = 06:30 UTC.
    alarm = make_alarm(weekdays=(FRIDAY,), hour=7, minute=30)
    occurrence = next_occurrence(alarm, utc(2026, 7, 3, 5, 0), LONDON)
    assert occurrence == utc(2026, 7, 3, 6, 30)


def test_repeating_rolls_a_passed_time_to_next_week() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=7, minute=30)
    occurrence = next_occurrence(alarm, utc(2026, 7, 3, 12, 0), LONDON)
    assert occurrence == utc(2026, 7, 10, 6, 30)


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------
def test_first_launch_evaluates_an_empty_window() -> None:
    alarm = make_alarm(weekdays=ALL_WEEKDAYS, hour=7, minute=30)
    result = evaluate(make_state(alarms=[alarm]), utc(2026, 7, 3, 6, 31), resolve_tz)
    assert result.ring == ()
    assert result.missed == ()


def test_master_off_silences_everything() -> None:
    alarm = make_alarm(weekdays=ALL_WEEKDAYS, hour=7, minute=30)
    snooze = SnoozeState("a1", utc(2026, 7, 3, 6, 30), 1, 10)
    state = make_state(
        alarms=[alarm],
        snooze_states=[snooze],
        master_enabled=False,
        last_evaluated_utc=utc(2026, 7, 3, 6, 0),
    )
    result = evaluate(state, utc(2026, 7, 3, 6, 31), resolve_tz)
    assert result.ring == ()
    assert result.missed == ()


def test_scheduled_occurrence_rings_on_time() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=7, minute=30)
    state = make_state(alarms=[alarm], last_evaluated_utc=utc(2026, 7, 3, 6, 29))
    result = evaluate(state, utc(2026, 7, 3, 6, 30, 10), resolve_tz)
    assert len(result.ring) == 1
    event = result.ring[0]
    assert event.alarm_id == "a1"
    assert event.occurrence_utc == utc(2026, 7, 3, 6, 30)
    assert not event.is_late
    assert not event.is_snooze_wakeup
    assert result.missed == ()


def test_scheduled_occurrence_within_grace_rings_late() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=7, minute=30)
    state = make_state(alarms=[alarm], last_evaluated_utc=utc(2026, 7, 3, 6, 29))
    result = evaluate(state, utc(2026, 7, 3, 6, 33), resolve_tz)
    assert len(result.ring) == 1
    assert result.ring[0].is_late


def test_scheduled_occurrence_beyond_grace_is_missed() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=7, minute=30)
    state = make_state(alarms=[alarm], last_evaluated_utc=utc(2026, 7, 3, 6, 29))
    result = evaluate(state, utc(2026, 7, 3, 6, 40), resolve_tz)
    assert result.ring == ()
    assert result.missed == (type(result.missed[0])("a1", utc(2026, 7, 3, 6, 30), 1),)


def test_multi_day_gap_rings_latest_and_reports_earlier_missed() -> None:
    alarm = make_alarm(weekdays=ALL_WEEKDAYS, hour=7, minute=30)
    state = make_state(alarms=[alarm], last_evaluated_utc=utc(2026, 6, 30, 12, 0))
    result = evaluate(state, utc(2026, 7, 3, 6, 30, 30), resolve_tz)
    assert len(result.ring) == 1
    assert result.ring[0].occurrence_utc == utc(2026, 7, 3, 6, 30)
    assert len(result.missed) == 1
    missed = result.missed[0]
    assert missed.occurrence_utc == utc(2026, 7, 2, 6, 30)
    assert missed.missed_count == 2


def test_multi_day_gap_with_no_recent_occurrence_is_all_missed() -> None:
    alarm = make_alarm(weekdays=ALL_WEEKDAYS, hour=7, minute=30)
    state = make_state(alarms=[alarm], last_evaluated_utc=utc(2026, 6, 30, 12, 0))
    result = evaluate(state, utc(2026, 7, 3, 12, 0), resolve_tz)
    assert result.ring == ()
    assert len(result.missed) == 1
    missed = result.missed[0]
    assert missed.occurrence_utc == utc(2026, 7, 3, 6, 30)
    assert missed.missed_count == 3


def test_disabled_alarm_never_fires() -> None:
    alarm = make_alarm(weekdays=ALL_WEEKDAYS, hour=7, minute=30, enabled=False)
    state = make_state(alarms=[alarm], last_evaluated_utc=utc(2026, 7, 3, 6, 0))
    result = evaluate(state, utc(2026, 7, 3, 6, 31), resolve_tz)
    assert result.ring == ()
    assert result.missed == ()


def test_alarm_with_no_occurrence_in_window_is_quiet() -> None:
    alarm = make_alarm(weekdays=(MONDAY,), hour=7, minute=30)
    state = make_state(alarms=[alarm], last_evaluated_utc=utc(2026, 7, 3, 6, 0))
    result = evaluate(state, utc(2026, 7, 3, 6, 31), resolve_tz)
    assert result.ring == ()
    assert result.missed == ()


def test_snooze_wakeup_rings_even_when_alarm_disabled() -> None:
    alarm = make_alarm(weekdays=(MONDAY,), hour=7, minute=30, enabled=False)
    snooze = SnoozeState("a1", utc(2026, 7, 3, 8, 0), 2, 15)
    state = make_state(
        alarms=[alarm],
        snooze_states=[snooze],
        last_evaluated_utc=utc(2026, 7, 3, 7, 59),
    )
    result = evaluate(state, utc(2026, 7, 3, 8, 0, 5), resolve_tz)
    assert len(result.ring) == 1
    event = result.ring[0]
    assert event.is_snooze_wakeup
    assert not event.is_late
    assert event.occurrence_utc == utc(2026, 7, 3, 8, 0)


def test_snooze_wakeup_beyond_grace_is_missed() -> None:
    alarm = make_alarm(weekdays=(MONDAY,), hour=7, minute=30)
    snooze = SnoozeState("a1", utc(2026, 7, 3, 8, 0), 1, 10)
    state = make_state(
        alarms=[alarm],
        snooze_states=[snooze],
        last_evaluated_utc=utc(2026, 7, 3, 7, 59),
    )
    result = evaluate(state, utc(2026, 7, 3, 8, 10), resolve_tz)
    assert result.ring == ()
    assert len(result.missed) == 1
    assert result.missed[0].occurrence_utc == utc(2026, 7, 3, 8, 0)
    assert result.missed[0].missed_count == 1


def test_snooze_wakeup_late_within_grace_flags_late() -> None:
    alarm = make_alarm(weekdays=(MONDAY,), hour=7, minute=30)
    snooze = SnoozeState("a1", utc(2026, 7, 3, 8, 0), 1, 10)
    state = make_state(
        alarms=[alarm],
        snooze_states=[snooze],
        last_evaluated_utc=utc(2026, 7, 3, 7, 59),
    )
    result = evaluate(state, utc(2026, 7, 3, 8, 3), resolve_tz)
    assert len(result.ring) == 1
    assert result.ring[0].is_late


def test_orphan_snooze_state_is_ignored() -> None:
    snooze = SnoozeState("ghost", utc(2026, 7, 3, 8, 0), 1, 10)
    state = make_state(
        snooze_states=[snooze], last_evaluated_utc=utc(2026, 7, 3, 7, 59)
    )
    result = evaluate(state, utc(2026, 7, 3, 8, 0, 5), resolve_tz)
    assert result.ring == ()
    assert result.missed == ()


def test_pending_snooze_outside_window_is_quiet() -> None:
    alarm = make_alarm(weekdays=(MONDAY,), hour=7, minute=30)
    snooze = SnoozeState("a1", utc(2026, 7, 3, 9, 0), 1, 10)
    state = make_state(
        alarms=[alarm],
        snooze_states=[snooze],
        last_evaluated_utc=utc(2026, 7, 3, 7, 59),
    )
    result = evaluate(state, utc(2026, 7, 3, 8, 0), resolve_tz)
    assert result.ring == ()
    assert result.missed == ()


# ---------------------------------------------------------------------------
# upcoming_occurrence
# ---------------------------------------------------------------------------
def test_upcoming_is_none_with_master_off() -> None:
    alarm = make_alarm(weekdays=ALL_WEEKDAYS, hour=7, minute=30)
    state = make_state(alarms=[alarm], master_enabled=False)
    assert upcoming_occurrence(state, utc(2026, 7, 3, 6, 0), resolve_tz) is None


def test_upcoming_picks_the_earliest_scheduled_alarm() -> None:
    early = make_alarm(alarm_id="early", weekdays=(FRIDAY,), hour=7, minute=0)
    late = make_alarm(alarm_id="late", weekdays=(FRIDAY,), hour=9, minute=0)
    state = make_state(alarms=[late, early])
    result = upcoming_occurrence(state, utc(2026, 7, 3, 5, 0), resolve_tz)
    assert result == ("early", utc(2026, 7, 3, 6, 0))


def test_upcoming_prefers_an_earlier_pending_snooze() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=9, minute=0)
    snooze = SnoozeState("a1", utc(2026, 7, 3, 5, 30), 1, 10)
    state = make_state(alarms=[alarm], snooze_states=[snooze])
    result = upcoming_occurrence(state, utc(2026, 7, 3, 5, 0), resolve_tz)
    assert result == ("a1", utc(2026, 7, 3, 5, 30))


def test_upcoming_ignores_expired_snoozes_orphans_and_disabled() -> None:
    disabled = make_alarm(alarm_id="off", weekdays=(FRIDAY,), enabled=False)
    done = make_alarm(
        alarm_id="done", weekdays=(), one_off_date=date(2026, 6, 1), hour=9, minute=0
    )
    expired = SnoozeState("off", utc(2026, 7, 3, 4, 0), 1, 10)
    orphan = SnoozeState("ghost", utc(2026, 7, 3, 5, 30), 1, 10)
    state = make_state(alarms=[disabled, done], snooze_states=[expired, orphan])
    assert upcoming_occurrence(state, utc(2026, 7, 3, 5, 0), resolve_tz) is None


def test_upcoming_keeps_the_earlier_of_two_snoozes() -> None:
    first = make_alarm(alarm_id="a1", weekdays=(FRIDAY,), hour=9, minute=0)
    second = make_alarm(alarm_id="a2", weekdays=(FRIDAY,), hour=9, minute=30)
    snoozes = [
        SnoozeState("a1", utc(2026, 7, 3, 5, 30), 1, 10),
        SnoozeState("a2", utc(2026, 7, 3, 6, 30), 1, 10),
    ]
    state = make_state(alarms=[first, second], snooze_states=snoozes)
    result = upcoming_occurrence(state, utc(2026, 7, 3, 5, 0), resolve_tz)
    assert result == ("a1", utc(2026, 7, 3, 5, 30))


def test_evaluate_result_tuples_are_immutable_dataclasses() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=7, minute=30)
    state = make_state(alarms=[alarm], last_evaluated_utc=utc(2026, 7, 3, 6, 29))
    result = evaluate(state, utc(2026, 7, 3, 6, 30, 10), resolve_tz)
    ring = result.ring[0]
    copied = type(ring)(
        ring.alarm_id, ring.occurrence_utc, ring.is_late, ring.is_snooze_wakeup
    )
    assert copied == ring


def test_grace_boundary_exactly_at_grace_still_rings() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=7, minute=30)
    state = make_state(alarms=[alarm], last_evaluated_utc=utc(2026, 7, 3, 6, 29))
    result = evaluate(state, utc(2026, 7, 3, 6, 30) + timedelta(minutes=5), resolve_tz)
    assert len(result.ring) == 1
    assert result.ring[0].is_late
