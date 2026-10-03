"""A damaged alarms file is kept aside and never crashes the load.

These run the real ``JsonAlarmStore`` over real files in a temporary folder.
The ones that matter most drive a real ``AlarmService`` through its first
tick, because the tick is what saves: a load that skipped entries followed by
a save is exactly how a damaged file used to be replaced, within a second of
starting, by the shortened state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fancyclock.application.alarms import AlarmService
from fancyclock.application.time_service import TimeService
from fancyclock.infrastructure.json_alarm_store import (
    ALARMS_FILE_NAME,
    JsonAlarmStore,
    _alarm_to_dict,
)
from tests.application.alarm_fakes import (
    FakeCatalog,
    FakeClock,
    FakePorter,
    FakeTimeSource,
    id_factory,
)
from tests.domain.test_alarms import make_alarm
from tests.infrastructure.test_json_alarm_store import full_state

UTC = timezone.utc
TRUNCATED_BYTES = 20
NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def service_over(store: JsonAlarmStore) -> AlarmService:
    clock = FakeClock(NOW)
    return AlarmService(
        store=store,
        catalog=FakeCatalog(),
        clock=clock,
        time_service=TimeService(source=FakeTimeSource(NOW), clock=clock),
        id_factory=id_factory(),
        porter=FakePorter(),
    )


def write_document(tmp_path: Path, document: object) -> Path:
    path = tmp_path / ALARMS_FILE_NAME
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def three_alarm_document() -> dict:
    alarms = [make_alarm(alarm_id=f"a{n}") for n in range(1, 4)]
    return {"version": 1, "alarms": [_alarm_to_dict(alarm) for alarm in alarms]}


def test_a_truncated_file_survives_the_first_tick(tmp_path: Path) -> None:
    path = write_document(tmp_path, three_alarm_document())
    original = path.read_bytes()
    path.write_bytes(original[:-TRUNCATED_BYTES])
    damaged = path.read_bytes()

    service = service_over(JsonAlarmStore(config_dir=tmp_path))
    service.tick()

    kept = service.damaged_copy_path
    assert kept is not None
    assert kept.parent == tmp_path
    assert kept.read_bytes() == damaged


def test_an_alarm_from_a_newer_build_survives_in_the_kept_copy(tmp_path) -> None:
    document = three_alarm_document()
    document["alarms"][1]["color"] = "orange"
    path = write_document(tmp_path, document)
    original = path.read_bytes()

    service = service_over(JsonAlarmStore(config_dir=tmp_path))
    service.tick()

    assert service.entries_lost_on_load == 1
    assert service.damaged_copy_path.read_bytes() == original


def test_a_second_damage_never_replaces_an_earlier_kept_copy(tmp_path) -> None:
    store = JsonAlarmStore(config_dir=tmp_path)
    path = tmp_path / ALARMS_FILE_NAME
    path.write_text("first damage", encoding="utf-8")
    first = store.load().kept_aside
    path.write_text("second damage", encoding="utf-8")
    second = store.load().kept_aside

    assert first != second
    assert first.read_text(encoding="utf-8") == "first damage"
    assert second.read_text(encoding="utf-8") == "second damage"


def refuse_copy(source: Path, target: Path) -> None:
    raise PermissionError(f"cannot copy {source} to {target}")


def test_a_failed_copy_refuses_every_save_so_the_original_stays(tmp_path):
    path = tmp_path / ALARMS_FILE_NAME
    path.write_text("damaged", encoding="utf-8")
    store = JsonAlarmStore(config_dir=tmp_path, copy_file=refuse_copy)

    assert store.load().kept_aside is None
    store.save(full_state())

    assert path.read_text(encoding="utf-8") == "damaged"
    assert sorted(p.name for p in tmp_path.iterdir()) == [ALARMS_FILE_NAME]


def test_a_clean_load_keeps_nothing_aside(tmp_path: Path) -> None:
    store = JsonAlarmStore(config_dir=tmp_path)
    store.save(full_state())
    assert store.load().kept_aside is None
    assert sorted(p.name for p in tmp_path.iterdir()) == [ALARMS_FILE_NAME]


def test_a_missing_file_keeps_nothing_aside(tmp_path: Path) -> None:
    assert JsonAlarmStore(config_dir=tmp_path).load().kept_aside is None


def test_a_null_alarm_list_is_a_whole_file_loss_not_a_crash(tmp_path) -> None:
    write_document(tmp_path, {"version": 1, "alarms": None})
    service = service_over(JsonAlarmStore(config_dir=tmp_path))
    assert service.alarms() == ()
    assert service.entries_lost_on_load >= 1
    assert service.damaged_copy_path is not None


def test_a_null_snooze_list_loses_the_snoozes_but_keeps_the_alarms(tmp_path):
    document = three_alarm_document()
    document["snooze_states"] = None
    write_document(tmp_path, document)
    service = service_over(JsonAlarmStore(config_dir=tmp_path))
    assert len(service.alarms()) == 3
    assert service.entries_lost_on_load >= 1


def test_a_naive_watermark_is_dropped_so_every_tick_still_runs(tmp_path) -> None:
    document = three_alarm_document()
    document["last_evaluated_utc"] = "2026-10-03T11:59:00"
    write_document(tmp_path, document)
    store = JsonAlarmStore(config_dir=tmp_path)
    assert store.load().state.last_evaluated_utc is None

    service = service_over(store)
    service.tick()
    service.tick()
