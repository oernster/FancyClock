"""Hand-written test doubles and builders for the AlarmService suite.

No mocking library is used anywhere in this project, so every port the
service depends on has a small fake here: the alarm store, the clock, the
time source, the timezone catalog (in a working and a raising form) and the
import/export porter. ``make_service`` wires them into a service under test
and ``state_with`` builds the state it starts from.

This module is imported by the test modules and is deliberately not named
``test_*``, so pytest does not collect it as a suite of its own.
"""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo

from fancyclock.application.alarms import AlarmService
from fancyclock.application.ports import AlarmLoad
from fancyclock.application.time_service import TimeService
from fancyclock.domain.alarms import Alarm, AlarmsState

UTC = timezone.utc


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


class FakeStore:
    """An alarm store that reports whatever the test says the load lost.

    ``skipped_alarms`` and ``skipped_snoozes`` default to zero, so the common
    case reads as a clean load and only the tests that care about damage have
    to mention it.
    """

    def __init__(
        self,
        state: AlarmsState | None = None,
        skipped_alarms: int = 0,
        skipped_snoozes: int = 0,
    ) -> None:
        self.state = state or AlarmsState.empty()
        self.skipped_alarms = skipped_alarms
        self.skipped_snoozes = skipped_snoozes
        self.save_count = 0

    def load(self) -> AlarmLoad:
        return AlarmLoad(
            state=self.state,
            skipped_alarms=self.skipped_alarms,
            skipped_snoozes=self.skipped_snoozes,
        )

    def save(self, state: AlarmsState) -> None:
        self.state = state
        self.save_count += 1


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def now_utc(self) -> datetime:
        return self.now


class FakeTimeSource:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def utc_time(self) -> datetime:
        return self.now


class FakeCatalog:
    def tzinfo_for(self, tz_id: str) -> tzinfo:
        return ZoneInfo(tz_id)


class RaisingCatalog:
    def tzinfo_for(self, tz_id: str) -> tzinfo:
        raise KeyError(tz_id)


class FakePorter:
    def __init__(self, to_import: tuple[Alarm, ...] = ()) -> None:
        self.exported: tuple[Alarm, ...] | None = None
        self.export_path: Path | None = None
        self.to_import = to_import

    def export_alarms(self, path: Path, alarms: tuple[Alarm, ...]) -> None:
        self.export_path = path
        self.exported = alarms

    def import_alarms(self, path: Path) -> tuple[Alarm, ...]:
        return self.to_import


def id_factory():
    counter = iter(range(1, 1000))

    def next_id() -> str:
        return f"id-{next(counter)}"

    return next_id


def make_service(
    now: datetime,
    state: AlarmsState | None = None,
    catalog=None,
    porter: FakePorter | None = None,
):
    store = FakeStore(state)
    clock = FakeClock(now)
    time_service = TimeService(source=FakeTimeSource(now), clock=clock)
    service = AlarmService(
        store=store,
        catalog=catalog or FakeCatalog(),
        clock=clock,
        time_service=time_service,
        id_factory=id_factory(),
        porter=porter or FakePorter(),
    )
    return service, store, clock


def state_with(alarms=(), snooze_states=(), last=None) -> AlarmsState:
    return AlarmsState(
        alarms=tuple(alarms),
        snooze_states=tuple(snooze_states),
        master_enabled=True,
        last_evaluated_utc=last,
    )
