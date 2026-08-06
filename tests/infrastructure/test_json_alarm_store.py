"""JsonAlarmStore and JsonAlarmPorter tests against real temp files."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from fancyclock.domain.alarms import (
    AlarmError,
    AlarmsState,
    SnoozeState,
)
from fancyclock.infrastructure.json_alarm_store import (
    JsonAlarmPorter,
    JsonAlarmStore,
    _alarm_to_dict,
)
from tests.domain.test_alarms import make_alarm

UTC = timezone.utc


def full_state() -> AlarmsState:
    repeating = make_alarm(alarm_id="rep", snooze_limit=3)
    one_off = make_alarm(
        alarm_id="once",
        weekdays=(),
        one_off_date=date(2026, 8, 1),
        label="Dentist",
        snooze_limit=None,
        enabled=False,
    )
    snooze = SnoozeState(
        alarm_id="rep",
        snoozed_until_utc=datetime(2026, 7, 3, 8, 0, tzinfo=UTC),
        snoozes_used=2,
        last_snooze_minutes=15,
    )
    return AlarmsState(
        alarms=(repeating, one_off),
        snooze_states=(snooze,),
        master_enabled=False,
        last_evaluated_utc=datetime(2026, 7, 3, 7, 59, tzinfo=UTC),
    )


def test_save_then_load_roundtrips_everything(tmp_path: Path) -> None:
    store = JsonAlarmStore(config_dir=tmp_path)
    state = full_state()
    store.save(state)
    assert store.load().state == state


def test_missing_file_loads_empty_state(tmp_path: Path) -> None:
    assert JsonAlarmStore(config_dir=tmp_path).load().state == AlarmsState.empty()


def test_corrupt_json_loads_empty_state(tmp_path: Path) -> None:
    store = JsonAlarmStore(config_dir=tmp_path)
    store.alarms_path().write_text("{nope", encoding="utf-8")
    assert store.load().state == AlarmsState.empty()


def test_non_dict_document_loads_empty_state(tmp_path: Path) -> None:
    store = JsonAlarmStore(config_dir=tmp_path)
    store.alarms_path().write_text("[1, 2]", encoding="utf-8")
    assert store.load().state == AlarmsState.empty()


def test_invalid_entries_are_skipped_on_load(tmp_path: Path) -> None:
    store = JsonAlarmStore(config_dir=tmp_path)
    good = _alarm_to_dict(make_alarm(alarm_id="good"))
    document = {
        "version": 1,
        "master_enabled": True,
        "last_evaluated_utc": "not-a-date",
        "alarms": [good, {"id": "bad", "hour": 99}],
        "snooze_states": [
            {
                "id": "good",
                "until": "2026-07-03T08:00:00+00:00",
                "used": 1,
                "last_minutes": 10,
            },
            {
                "id": "orphan",
                "until": "2026-07-03T08:00:00+00:00",
                "used": 1,
                "last_minutes": 10,
            },
            {"id": "good", "until": "junk", "used": 1, "last_minutes": 10},
        ],
    }
    store.alarms_path().write_text(json.dumps(document), encoding="utf-8")
    state = store.load().state
    assert [a.alarm_id for a in state.alarms] == ["good"]
    assert len(state.snooze_states) == 1
    assert state.snooze_states[0].alarm_id == "good"
    assert state.last_evaluated_utc is None


def test_master_enabled_survives_odd_values(tmp_path: Path) -> None:
    store = JsonAlarmStore(config_dir=tmp_path)
    document = {"version": 1, "master_enabled": False, "alarms": []}
    store.alarms_path().write_text(json.dumps(document), encoding="utf-8")
    assert store.load().state.master_enabled is False


def test_porter_roundtrip(tmp_path: Path) -> None:
    porter = JsonAlarmPorter()
    alarms = (make_alarm(alarm_id="x"), make_alarm(alarm_id="y", hour=9))
    target = tmp_path / "export.json"
    porter.export_alarms(target, alarms)
    assert porter.import_alarms(target) == alarms


def test_porter_import_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(AlarmError):
        JsonAlarmPorter().import_alarms(tmp_path / "nothing.json")


def test_porter_import_bad_json_raises(tmp_path: Path) -> None:
    target = tmp_path / "bad.json"
    target.write_text("{nope", encoding="utf-8")
    with pytest.raises(AlarmError):
        JsonAlarmPorter().import_alarms(target)


def test_porter_import_non_dict_raises(tmp_path: Path) -> None:
    target = tmp_path / "list.json"
    target.write_text("[]", encoding="utf-8")
    with pytest.raises(AlarmError):
        JsonAlarmPorter().import_alarms(target)


def test_porter_import_wrong_version_raises(tmp_path: Path) -> None:
    target = tmp_path / "wrong.json"
    target.write_text(json.dumps({"version": 99, "alarms": []}), encoding="utf-8")
    with pytest.raises(AlarmError):
        JsonAlarmPorter().import_alarms(target)


def test_porter_import_missing_alarm_list_raises(tmp_path: Path) -> None:
    target = tmp_path / "empty.json"
    target.write_text(json.dumps({"version": 1}), encoding="utf-8")
    with pytest.raises(AlarmError):
        JsonAlarmPorter().import_alarms(target)


def test_porter_import_invalid_alarm_raises(tmp_path: Path) -> None:
    target = tmp_path / "invalid.json"
    bad = _alarm_to_dict(make_alarm())
    bad["hour"] = 99
    target.write_text(json.dumps({"version": 1, "alarms": [bad]}), encoding="utf-8")
    with pytest.raises(AlarmError):
        JsonAlarmPorter().import_alarms(target)


def test_porter_import_malformed_alarm_entry_raises(tmp_path: Path) -> None:
    target = tmp_path / "malformed.json"
    document = {"version": 1, "alarms": [{"id": "x"}]}
    target.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(AlarmError):
        JsonAlarmPorter().import_alarms(target)


def test_load_counts_a_malformed_alarm_entry(tmp_path) -> None:
    """A bad entry is skipped as before, now counted rather than hidden."""
    store = JsonAlarmStore(config_dir=tmp_path)
    store.alarms_path().write_text(
        json.dumps(
            {
                "version": 1,
                "alarms": [{"id": "only-an-id"}],
                "snooze_states": [],
            }
        ),
        encoding="utf-8",
    )
    load = store.load()
    assert load.state.alarms == ()
    assert load.skipped_alarms == 1
    assert load.lost_entries == 1


def test_load_counts_a_malformed_snooze_record(tmp_path) -> None:
    store = JsonAlarmStore(config_dir=tmp_path)
    store.alarms_path().write_text(
        json.dumps(
            {
                "version": 1,
                "alarms": [],
                "snooze_states": [{"id": "x"}],
            }
        ),
        encoding="utf-8",
    )
    load = store.load()
    assert load.skipped_snoozes == 1
    assert load.skipped_alarms == 0


def test_load_reports_the_whole_file_when_the_json_is_unreadable(tmp_path) -> None:
    store = JsonAlarmStore(config_dir=tmp_path)
    store.alarms_path().write_text("{not json", encoding="utf-8")
    load = store.load()
    assert load.state.alarms == ()
    assert load.lost_entries == 1


def test_load_reports_the_whole_file_when_the_document_is_the_wrong_shape(
    tmp_path,
) -> None:
    store = JsonAlarmStore(config_dir=tmp_path)
    store.alarms_path().write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    load = store.load()
    assert load.lost_entries == 1


def test_a_missing_file_is_a_first_run_rather_than_damage(tmp_path) -> None:
    load = JsonAlarmStore(config_dir=tmp_path / "absent").load()
    assert load.state.alarms == ()
    assert load.lost_entries == 0


def test_an_unparseable_watermark_loses_no_entry(tmp_path) -> None:
    """The watermark falls back to None; nothing the user set is lost by it."""
    store = JsonAlarmStore(config_dir=tmp_path)
    store.alarms_path().write_text(
        json.dumps(
            {"version": 1, "alarms": [], "last_evaluated_utc": "not-a-timestamp"}
        ),
        encoding="utf-8",
    )
    load = store.load()
    assert load.state.last_evaluated_utc is None
    assert load.lost_entries == 0
