"""Pure alarm scheduling: occurrence math, DST policy and tick evaluation.

All functions receive time and timezone objects from the caller; nothing
here reads the wall clock. The DST policy is: a wall time that does not
exist (spring-forward gap) fires at the first valid instant after the gap;
an ambiguous wall time (fall-back) fires on its first occurrence only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone, tzinfo
from typing import Callable

from fancyclock.domain.alarms import Alarm, AlarmsState

MISSED_GRACE = timedelta(minutes=5)
LATE_TOLERANCE = timedelta(seconds=90)
GAP_STEP = timedelta(minutes=1)

TzResolver = Callable[[str], tzinfo]


@dataclass(frozen=True, slots=True)
class RingEvent:
    """An alarm that should ring now."""

    alarm_id: str
    occurrence_utc: datetime
    is_late: bool
    is_snooze_wakeup: bool


@dataclass(frozen=True, slots=True)
class MissedEvent:
    """Occurrences that passed too long ago to ring."""

    alarm_id: str
    occurrence_utc: datetime
    missed_count: int


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """The outcome of evaluating one tick window."""

    ring: tuple[RingEvent, ...]
    missed: tuple[MissedEvent, ...]


def resolve_wall_time(wall: datetime, tz: tzinfo) -> datetime:
    """Return the aware UTC instant for a naive wall time in ``tz``.

    Applies the DST policy: nonexistent wall times step forward to the
    first valid instant; ambiguous wall times take the earlier instant.
    """
    while True:
        first = wall.replace(tzinfo=tz, fold=0)
        second = wall.replace(tzinfo=tz, fold=1)
        if first.utcoffset() == second.utcoffset():
            return first.astimezone(timezone.utc)
        round_trip = first.astimezone(timezone.utc).astimezone(tz)
        if round_trip.replace(tzinfo=None) == wall:
            return first.astimezone(timezone.utc)
        wall = wall + GAP_STEP


def next_occurrence(alarm: Alarm, after_utc: datetime, tz: tzinfo) -> datetime | None:
    """Return the alarm's next UTC occurrence strictly after ``after_utc``.

    Returns ``None`` for a one-off alarm whose date has already passed.
    """
    at = time(alarm.hour, alarm.minute)
    if alarm.one_off_date is not None:
        instant = resolve_wall_time(datetime.combine(alarm.one_off_date, at), tz)
        return instant if instant > after_utc else None
    local_date = after_utc.astimezone(tz).date()
    while True:
        if local_date.weekday() in alarm.weekdays:
            instant = resolve_wall_time(datetime.combine(local_date, at), tz)
            if instant > after_utc:
                return instant
        local_date = local_date + timedelta(days=1)


def _occurrences_between(
    alarm: Alarm, start_utc: datetime, end_utc: datetime, tz: tzinfo
) -> tuple[datetime, ...]:
    """Return every occurrence in ``(start_utc, end_utc]`` in order."""
    found: list[datetime] = []
    occurrence = next_occurrence(alarm, start_utc, tz)
    while occurrence is not None and occurrence <= end_utc:
        found.append(occurrence)
        occurrence = next_occurrence(alarm, occurrence, tz)
    return tuple(found)


def evaluate(
    state: AlarmsState, now_utc: datetime, resolve_tz: TzResolver
) -> EvaluationResult:
    """Evaluate one tick: what rings now and what was missed.

    The window is ``(last_evaluated_utc, now_utc]``; a fresh state (no
    ``last_evaluated_utc``) evaluates an empty window so a first launch
    never fires stale occurrences. Snooze wakeups fire regardless of the
    alarm's enabled flag (the episode was already granted); the master
    switch silences everything.
    """
    if not state.master_enabled:
        return EvaluationResult(ring=(), missed=())
    start = state.last_evaluated_utc or now_utc
    ring: list[RingEvent] = []
    missed: list[MissedEvent] = []

    for snooze in state.snooze_states:
        if state.alarm_by_id(snooze.alarm_id) is None:
            continue
        wakeup = snooze.snoozed_until_utc
        if not start < wakeup <= now_utc:
            continue
        if now_utc - wakeup <= MISSED_GRACE:
            ring.append(
                RingEvent(
                    alarm_id=snooze.alarm_id,
                    occurrence_utc=wakeup,
                    is_late=now_utc - wakeup > LATE_TOLERANCE,
                    is_snooze_wakeup=True,
                )
            )
        else:
            missed.append(
                MissedEvent(
                    alarm_id=snooze.alarm_id,
                    occurrence_utc=wakeup,
                    missed_count=1,
                )
            )

    for alarm in state.alarms:
        if not alarm.enabled:
            continue
        occurrences = _occurrences_between(
            alarm, start, now_utc, resolve_tz(alarm.tz_id)
        )
        if not occurrences:
            continue
        latest = occurrences[-1]
        if now_utc - latest <= MISSED_GRACE:
            if len(occurrences) > 1:
                missed.append(
                    MissedEvent(
                        alarm_id=alarm.alarm_id,
                        occurrence_utc=occurrences[-2],
                        missed_count=len(occurrences) - 1,
                    )
                )
            ring.append(
                RingEvent(
                    alarm_id=alarm.alarm_id,
                    occurrence_utc=latest,
                    is_late=now_utc - latest > LATE_TOLERANCE,
                    is_snooze_wakeup=False,
                )
            )
        else:
            missed.append(
                MissedEvent(
                    alarm_id=alarm.alarm_id,
                    occurrence_utc=latest,
                    missed_count=len(occurrences),
                )
            )

    return EvaluationResult(ring=tuple(ring), missed=tuple(missed))


def upcoming_occurrence(
    state: AlarmsState, now_utc: datetime, resolve_tz: TzResolver
) -> tuple[str, datetime] | None:
    """Return the next (alarm_id, UTC instant) to fire, or ``None``.

    Considers enabled alarms and pending snooze wakeups; respects the
    master switch.
    """
    if not state.master_enabled:
        return None
    best: tuple[str, datetime] | None = None

    for snooze in state.snooze_states:
        if state.alarm_by_id(snooze.alarm_id) is None:
            continue
        if snooze.snoozed_until_utc <= now_utc:
            continue
        if best is None or snooze.snoozed_until_utc < best[1]:
            best = (snooze.alarm_id, snooze.snoozed_until_utc)

    for alarm in state.alarms:
        if not alarm.enabled:
            continue
        occurrence = next_occurrence(alarm, now_utc, resolve_tz(alarm.tz_id))
        if occurrence is None:
            continue
        if best is None or occurrence < best[1]:
            best = (alarm.alarm_id, occurrence)

    return best
