"""Alarm orchestration: CRUD, tick evaluation, snoozing and import/export.

The service owns the in-memory ``AlarmsState`` and persists through the
``AlarmStore`` port. Every state mutation persists immediately; the
per-tick ``last_evaluated_utc`` watermark is throttled so the store is
not rewritten every second.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Callable

from fancyclock.application.ports import (
    AlarmPorter,
    AlarmStore,
    Clock,
    TimezoneCatalog,
)
from fancyclock.application.time_service import TimeService
from fancyclock.domain.alarm_schedule import evaluate, upcoming_occurrence
from fancyclock.domain.alarms import Alarm, AlarmsState, SnoozeState

WATERMARK_PERSIST_INTERVAL = timedelta(seconds=60)
MINUTES = timedelta(minutes=1)


@dataclass(frozen=True, slots=True)
class RingingAlarm:
    """A resolved alarm that should ring now."""

    alarm: Alarm
    occurrence_utc: datetime
    is_late: bool
    is_snooze_wakeup: bool


@dataclass(frozen=True, slots=True)
class MissedAlarm:
    """A resolved alarm whose occurrences passed too long ago to ring."""

    alarm: Alarm
    occurrence_utc: datetime
    missed_count: int


@dataclass(frozen=True, slots=True)
class TickResult:
    """The outcome of one service tick."""

    ringing: tuple[RingingAlarm, ...]
    missed: tuple[MissedAlarm, ...]


@dataclass(frozen=True, slots=True)
class NextAlarmInfo:
    """The next alarm to fire and when."""

    alarm: Alarm
    occurrence_utc: datetime


class AlarmService:
    """Coordinates alarm state, scheduling and persistence."""

    def __init__(
        self,
        store: AlarmStore,
        catalog: TimezoneCatalog,
        clock: Clock,
        time_service: TimeService,
        id_factory: Callable[[], str],
        porter: AlarmPorter,
    ) -> None:
        self._store = store
        self._catalog = catalog
        self._clock = clock
        self._time_service = time_service
        self._id_factory = id_factory
        self._porter = porter
        self._load = store.load()
        self._state = self._load.state
        self._watermark_persisted_at: datetime | None = None

    @property
    def entries_lost_on_load(self) -> int:
        """Return how many stored entries could not be read at startup.

        Zero means the saved document loaded whole. Anything else is an alarm
        or a snooze the user set that is no longer there, which is worth
        telling them once rather than leaving them to notice a silent morning.
        """
        return self._load.lost_entries

    # ------------------------------------------------------------------
    # Time and lookups
    # ------------------------------------------------------------------
    def now_utc(self) -> datetime:
        """Return the NTP-corrected current time as an aware UTC datetime."""
        offset = timedelta(seconds=self._time_service.offset_seconds)
        return self._clock.now_utc() + offset

    def _resolve_tz(self, tz_id: str) -> tzinfo:
        """Resolve a timezone id, falling back to UTC for unknown zones."""
        try:
            return self._catalog.tzinfo_for(tz_id)
        except (KeyError, TypeError, ValueError):
            # The port promises to raise when the zone is unknown. An
            # unknown name is a KeyError (ZoneInfoNotFoundError derives
            # from it), a malformed one a ValueError, a non-string a
            # TypeError. UTC is the safe reading; a broken catalog is not
            # this method's business to hide.
            return timezone.utc

    def now_in(self, tz_id: str) -> datetime:
        """Return the NTP-corrected current time in ``tz_id``."""
        return self.now_utc().astimezone(self._resolve_tz(tz_id))

    def alarms(self) -> tuple[Alarm, ...]:
        """Return every alarm sorted by time then label."""
        return tuple(
            sorted(
                self._state.alarms,
                key=lambda a: (a.hour, a.minute, a.label, a.alarm_id),
            )
        )

    def alarm_by_id(self, alarm_id: str) -> Alarm | None:
        """Return the alarm with ``alarm_id``, else ``None``."""
        return self._state.alarm_by_id(alarm_id)

    def new_alarm_id(self) -> str:
        """Return a fresh unique alarm identifier."""
        return self._id_factory()

    def master_enabled(self) -> bool:
        """Return the master switch state."""
        return self._state.master_enabled

    def set_master_enabled(self, enabled: bool) -> None:
        """Set the master switch and persist."""
        self._save(replace(self._state, master_enabled=bool(enabled)))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def upsert(self, alarm: Alarm) -> None:
        """Add or replace an alarm; editing cancels any live snooze."""
        existing = self._state.alarm_by_id(alarm.alarm_id)
        if existing is None:
            alarms = self._state.alarms + (alarm,)
        else:
            alarms = tuple(
                alarm if a.alarm_id == alarm.alarm_id else a for a in self._state.alarms
            )
        self._save(
            replace(
                self._state,
                alarms=alarms,
                snooze_states=self._without_snooze(alarm.alarm_id),
            )
        )

    def delete(self, alarm_id: str) -> None:
        """Remove an alarm and any live snooze; persist."""
        alarms = tuple(a for a in self._state.alarms if a.alarm_id != alarm_id)
        self._save(
            replace(
                self._state,
                alarms=alarms,
                snooze_states=self._without_snooze(alarm_id),
            )
        )

    def set_enabled(self, alarm_id: str, enabled: bool) -> None:
        """Enable or disable one alarm; disabling cancels any live snooze."""
        alarm = self._state.alarm_by_id(alarm_id)
        if alarm is None:
            return
        alarms = tuple(
            replace(a, enabled=bool(enabled)) if a.alarm_id == alarm_id else a
            for a in self._state.alarms
        )
        snoozes = (
            self._without_snooze(alarm_id) if not enabled else self._state.snooze_states
        )
        self._save(replace(self._state, alarms=alarms, snooze_states=snoozes))

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------
    def tick(self) -> TickResult:
        """Evaluate the window since the last tick and apply consequences."""
        now = self.now_utc()
        result = evaluate(self._state, now, self._resolve_tz)

        state = self._state
        for event in result.ring:
            if event.is_snooze_wakeup:
                continue
            state = replace(
                state,
                snooze_states=tuple(
                    s for s in state.snooze_states if s.alarm_id != event.alarm_id
                ),
            )
            state = self._disable_if_one_off(state, event.alarm_id)
        for event in result.missed:
            state = self._disable_if_one_off(state, event.alarm_id)

        changed = state is not self._state
        state = replace(state, last_evaluated_utc=now)
        self._state = state
        if changed or self._watermark_due(now):
            self._persist(now)

        return TickResult(
            ringing=tuple(
                RingingAlarm(
                    alarm=self._state.alarm_by_id(e.alarm_id),
                    occurrence_utc=e.occurrence_utc,
                    is_late=e.is_late,
                    is_snooze_wakeup=e.is_snooze_wakeup,
                )
                for e in result.ring
            ),
            missed=tuple(
                MissedAlarm(
                    alarm=self._state.alarm_by_id(e.alarm_id),
                    occurrence_utc=e.occurrence_utc,
                    missed_count=e.missed_count,
                )
                for e in result.missed
            ),
        )

    # ------------------------------------------------------------------
    # Snoozing
    # ------------------------------------------------------------------
    def snooze(self, alarm_id: str, minutes: int) -> None:
        """Snooze the ringing alarm for ``minutes``; persists the episode."""
        now = self.now_utc()
        existing = self._state.snooze_for(alarm_id)
        used = existing.snoozes_used + 1 if existing else 1
        new_state = SnoozeState(
            alarm_id=alarm_id,
            snoozed_until_utc=now + minutes * MINUTES,
            snoozes_used=used,
            last_snooze_minutes=minutes,
        )
        snoozes = self._without_snooze(alarm_id) + (new_state,)
        self._save(replace(self._state, snooze_states=snoozes))

    def dismiss(self, alarm_id: str) -> None:
        """End the ringing episode for an alarm."""
        self._save(replace(self._state, snooze_states=self._without_snooze(alarm_id)))

    def snoozes_remaining(self, alarm_id: str) -> int | None:
        """Return remaining snoozes this episode; ``None`` means unlimited."""
        alarm = self._state.alarm_by_id(alarm_id)
        if alarm is None or alarm.snooze_limit is None:
            return None
        state = self._state.snooze_for(alarm_id)
        used = state.snoozes_used if state else 0
        return max(0, alarm.snooze_limit - used)

    def effective_snooze_minutes(self, alarm_id: str) -> int:
        """Return the snooze duration the Snooze button should apply now."""
        state = self._state.snooze_for(alarm_id)
        if state is not None:
            return state.last_snooze_minutes
        alarm = self._state.alarm_by_id(alarm_id)
        return alarm.snooze_minutes if alarm else 0

    # ------------------------------------------------------------------
    # Summary, import and export
    # ------------------------------------------------------------------
    def next_alarm(self) -> NextAlarmInfo | None:
        """Return the next alarm to fire, else ``None``."""
        found = upcoming_occurrence(self._state, self.now_utc(), self._resolve_tz)
        if found is None:
            return None
        alarm_id, occurrence = found
        return NextAlarmInfo(
            alarm=self._state.alarm_by_id(alarm_id), occurrence_utc=occurrence
        )

    def export_alarms(self, path: Path) -> int:
        """Export every alarm to ``path``; returns the count."""
        self._porter.export_alarms(path, self._state.alarms)
        return len(self._state.alarms)

    def import_alarms(self, path: Path) -> int:
        """Import alarms from ``path`` as new entries; returns the count."""
        imported = self._porter.import_alarms(path)
        fresh = tuple(replace(alarm, alarm_id=self._id_factory()) for alarm in imported)
        self._save(replace(self._state, alarms=self._state.alarms + fresh))
        return len(fresh)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _without_snooze(self, alarm_id: str) -> tuple[SnoozeState, ...]:
        return tuple(s for s in self._state.snooze_states if s.alarm_id != alarm_id)

    def _disable_if_one_off(self, state: AlarmsState, alarm_id: str) -> AlarmsState:
        alarm = state.alarm_by_id(alarm_id)
        if alarm is None or alarm.is_repeating or not alarm.enabled:
            return state
        return replace(
            state,
            alarms=tuple(
                replace(a, enabled=False) if a.alarm_id == alarm_id else a
                for a in state.alarms
            ),
        )

    def _watermark_due(self, now: datetime) -> bool:
        if self._watermark_persisted_at is None:
            return True
        return now - self._watermark_persisted_at >= WATERMARK_PERSIST_INTERVAL

    def _persist(self, now: datetime) -> None:
        self._store.save(self._state)
        self._watermark_persisted_at = now

    def _save(self, state: AlarmsState) -> None:
        self._state = state
        self._store.save(state)
