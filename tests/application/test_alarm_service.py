"""AlarmService tests using hand-written fakes for every port."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fancyclock.application.alarms import AlarmService
from fancyclock.application.time_service import TimeService
from fancyclock.domain.alarms import FRIDAY
from tests.application.alarm_fakes import (
    FakeCatalog,
    FakeClock,
    FakePorter,
    FakeStore,
    FakeTimeSource,
    RaisingCatalog,
    id_factory,
    make_service,
    state_with,
    utc,
)
from tests.domain.test_alarms import make_alarm


def test_now_utc_applies_the_ntp_offset() -> None:
    now = utc(2026, 7, 3, 6, 0)
    store = FakeStore()
    clock = FakeClock(now)
    time_service = TimeService(
        source=FakeTimeSource(now + timedelta(seconds=120)), clock=clock
    )
    time_service.synchronize()
    service = AlarmService(
        store=store,
        catalog=FakeCatalog(),
        clock=clock,
        time_service=time_service,
        id_factory=id_factory(),
        porter=FakePorter(),
    )
    assert service.now_utc() == now + timedelta(seconds=120)


def test_alarms_are_sorted_by_time_then_label() -> None:
    late = make_alarm(alarm_id="b", hour=9, minute=0, label="B")
    early = make_alarm(alarm_id="a", hour=7, minute=0, label="A")
    same = make_alarm(alarm_id="c", hour=7, minute=0, label="Z")
    service, _, _ = make_service(
        utc(2026, 7, 3, 6, 0), state_with(alarms=[late, same, early])
    )
    assert [a.alarm_id for a in service.alarms()] == ["a", "c", "b"]


def test_upsert_adds_then_replaces_and_clears_snooze() -> None:
    now = utc(2026, 7, 3, 6, 0)
    service, store, _ = make_service(now)
    alarm = make_alarm(alarm_id="a1", hour=7)
    service.upsert(alarm)
    assert service.alarm_by_id("a1") == alarm

    service.snooze("a1", 10)
    assert store.state.snooze_for("a1") is not None

    edited = make_alarm(alarm_id="a1", hour=8)
    service.upsert(edited)
    assert service.alarm_by_id("a1").hour == 8
    assert store.state.snooze_for("a1") is None
    assert len(store.state.alarms) == 1


def test_delete_removes_alarm_and_snooze() -> None:
    now = utc(2026, 7, 3, 6, 0)
    service, store, _ = make_service(now, state_with(alarms=[make_alarm()]))
    service.snooze("a1", 5)
    service.delete("a1")
    assert store.state.alarms == ()
    assert store.state.snooze_states == ()


def test_set_enabled_toggles_and_disabling_cancels_snooze() -> None:
    now = utc(2026, 7, 3, 6, 0)
    service, store, _ = make_service(now, state_with(alarms=[make_alarm()]))
    service.snooze("a1", 5)

    service.set_enabled("a1", False)
    assert not service.alarm_by_id("a1").enabled
    assert store.state.snooze_for("a1") is None

    service.set_enabled("a1", True)
    assert service.alarm_by_id("a1").enabled

    before = store.save_count
    service.set_enabled("missing", False)
    assert store.save_count == before


def test_master_switch_roundtrip() -> None:
    service, store, _ = make_service(utc(2026, 7, 3, 6, 0))
    assert service.master_enabled()
    service.set_master_enabled(False)
    assert not service.master_enabled()
    assert not store.state.master_enabled


def test_tick_rings_a_scheduled_alarm_and_resets_its_episode() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=7, minute=30)
    state = state_with(alarms=[alarm], last=utc(2026, 7, 3, 6, 29))
    service, store, _ = make_service(utc(2026, 7, 3, 6, 30, 10), state)
    service.snooze("a1", 10)

    result = service.tick()
    assert len(result.ringing) == 1
    ringing = result.ringing[0]
    assert ringing.alarm.alarm_id == "a1"
    assert not ringing.is_snooze_wakeup
    assert store.state.snooze_for("a1") is None
    assert store.state.last_evaluated_utc == utc(2026, 7, 3, 6, 30, 10)


def test_tick_disables_a_rung_one_off() -> None:
    alarm = make_alarm(
        weekdays=(),
        one_off_date=utc(2026, 7, 3, 0, 0).date(),
        hour=7,
        minute=30,
        tz_id="UTC",
    )
    state = state_with(alarms=[alarm], last=utc(2026, 7, 3, 7, 29))
    service, store, _ = make_service(utc(2026, 7, 3, 7, 30, 5), state)
    result = service.tick()
    assert len(result.ringing) == 1
    assert not store.state.alarm_by_id("a1").enabled


def test_tick_disables_a_missed_one_off_and_reports_it() -> None:
    alarm = make_alarm(
        weekdays=(),
        one_off_date=utc(2026, 7, 3, 0, 0).date(),
        hour=7,
        minute=30,
        tz_id="UTC",
    )
    state = state_with(alarms=[alarm], last=utc(2026, 7, 3, 7, 29))
    service, store, _ = make_service(utc(2026, 7, 3, 8, 30), state)
    result = service.tick()
    assert result.ringing == ()
    assert len(result.missed) == 1
    assert result.missed[0].alarm.alarm_id == "a1"
    assert result.missed[0].missed_count == 1
    assert not store.state.alarm_by_id("a1").enabled


def test_tick_snooze_wakeup_keeps_the_episode_state() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=7, minute=30)
    state = state_with(alarms=[alarm], last=utc(2026, 7, 3, 6, 40))
    service, store, clock = make_service(utc(2026, 7, 3, 6, 41), state)
    service.snooze("a1", 10)

    assert store.state.snooze_for("a1").snoozed_until_utc == utc(2026, 7, 3, 6, 51)

    clock.now = utc(2026, 7, 3, 6, 51, 5)
    result = service.tick()
    assert len(result.ringing) == 1
    assert result.ringing[0].is_snooze_wakeup
    assert store.state.snooze_for("a1") is not None


def test_tick_watermark_persistence_is_throttled() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=23, minute=59)
    state = state_with(alarms=[alarm], last=utc(2026, 7, 3, 6, 0))
    service, store, clock = make_service(utc(2026, 7, 3, 6, 0, 1), state)

    service.tick()
    first = store.save_count
    assert first == 1

    clock.now = utc(2026, 7, 3, 6, 0, 30)
    service.tick()
    assert store.save_count == first

    clock.now = utc(2026, 7, 3, 6, 2, 0)
    service.tick()
    assert store.save_count == first + 1


def test_snooze_creates_then_increments_the_episode() -> None:
    now = utc(2026, 7, 3, 6, 0)
    service, store, _ = make_service(now, state_with(alarms=[make_alarm()]))
    service.snooze("a1", 15)
    state = store.state.snooze_for("a1")
    assert state.snoozes_used == 1
    assert state.last_snooze_minutes == 15
    assert state.snoozed_until_utc == now + timedelta(minutes=15)

    service.snooze("a1", 5)
    state = store.state.snooze_for("a1")
    assert state.snoozes_used == 2
    assert state.last_snooze_minutes == 5


def test_dismiss_clears_the_episode() -> None:
    service, store, _ = make_service(
        utc(2026, 7, 3, 6, 0), state_with(alarms=[make_alarm()])
    )
    service.snooze("a1", 5)
    service.dismiss("a1")
    assert store.state.snooze_for("a1") is None


def test_snoozes_remaining_math() -> None:
    limited = make_alarm(alarm_id="lim", snooze_limit=2)
    unlimited = make_alarm(alarm_id="unlim", snooze_limit=None)
    service, _, _ = make_service(
        utc(2026, 7, 3, 6, 0), state_with(alarms=[limited, unlimited])
    )
    assert service.snoozes_remaining("unlim") is None
    assert service.snoozes_remaining("missing") is None
    assert service.snoozes_remaining("lim") == 2
    service.snooze("lim", 5)
    assert service.snoozes_remaining("lim") == 1
    service.snooze("lim", 5)
    assert service.snoozes_remaining("lim") == 0
    service.snooze("lim", 5)
    assert service.snoozes_remaining("lim") == 0


def test_effective_snooze_minutes_follows_the_episode() -> None:
    alarm = make_alarm(snooze_minutes=10)
    service, _, _ = make_service(utc(2026, 7, 3, 6, 0), state_with(alarms=[alarm]))
    assert service.effective_snooze_minutes("a1") == 10
    service.snooze("a1", 30)
    assert service.effective_snooze_minutes("a1") == 30
    assert service.effective_snooze_minutes("missing") == 0


def test_next_alarm_resolves_or_returns_none() -> None:
    service, _, _ = make_service(utc(2026, 7, 3, 6, 0))
    assert service.next_alarm() is None

    alarm = make_alarm(weekdays=(FRIDAY,), hour=9, minute=0, tz_id="UTC")
    service.upsert(alarm)
    info = service.next_alarm()
    assert info.alarm.alarm_id == "a1"
    assert info.occurrence_utc == utc(2026, 7, 3, 9, 0)


def test_export_passes_alarms_to_the_porter() -> None:
    alarm = make_alarm()
    porter = FakePorter()
    service, _, _ = make_service(
        utc(2026, 7, 3, 6, 0), state_with(alarms=[alarm]), porter=porter
    )
    count = service.export_alarms(Path("out.json"))
    assert count == 1
    assert porter.export_path == Path("out.json")
    assert porter.exported == (alarm,)


def test_import_appends_with_fresh_ids() -> None:
    incoming = (make_alarm(alarm_id="foreign"),)
    porter = FakePorter(to_import=incoming)
    service, store, _ = make_service(
        utc(2026, 7, 3, 6, 0), state_with(alarms=[make_alarm()]), porter=porter
    )
    count = service.import_alarms(Path("in.json"))
    assert count == 1
    assert len(store.state.alarms) == 2
    ids = {a.alarm_id for a in store.state.alarms}
    assert "foreign" not in ids
    assert "a1" in ids


def test_unknown_timezone_falls_back_to_utc() -> None:
    alarm = make_alarm(weekdays=(FRIDAY,), hour=7, minute=30, tz_id="Nowhere/Bad")
    state = state_with(alarms=[alarm], last=utc(2026, 7, 3, 7, 29))
    service, _, _ = make_service(
        utc(2026, 7, 3, 7, 30, 5), state, catalog=RaisingCatalog()
    )
    result = service.tick()
    assert len(result.ringing) == 1
    assert result.ringing[0].occurrence_utc == utc(2026, 7, 3, 7, 30)


def test_new_alarm_id_uses_the_injected_factory() -> None:
    service, _, _ = make_service(utc(2026, 7, 3, 6, 0))
    assert service.new_alarm_id() == "id-1"
    assert service.new_alarm_id() == "id-2"


def test_now_in_converts_to_the_requested_timezone() -> None:
    service, _, _ = make_service(utc(2026, 7, 3, 6, 0))
    local = service.now_in("Europe/London")
    assert (local.hour, local.minute) == (7, 0)
    fallback = service.now_in("Nowhere/Bad")
    assert (fallback.hour, fallback.minute) == (6, 0)
