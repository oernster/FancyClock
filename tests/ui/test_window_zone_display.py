"""The face shows the zone the alarms ring by.

Alarms resolve a zone through zoneinfo with the shipped tzdata. The face used
to convert through Qt's own zone data, which disagrees for some zones (an
hour out in Scoresbysund) and does not know others at all (Coyhaique). A
07:00 alarm could ring while the face showed 06:00; in an unknown zone the
face went blank.
Each test builds the real window offscreen over a temporary settings folder.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from tests.ui.test_window_skin_persistence import _build_window

DISAGREEING_ZONE = "America/Scoresbysund"
ZONE_QT_DOES_NOT_KNOW = "America/Coyhaique"


def zoneinfo_offset_now(tz_id: str) -> int:
    now = datetime.now(timezone.utc)
    return int(now.astimezone(ZoneInfo(tz_id)).utcoffset().total_seconds())


def test_the_face_uses_the_alarm_zone_data(qapp, tmp_path) -> None:
    window = _build_window(tmp_path)
    window._change_timezone(DISAGREEING_ZONE)

    shown = window._current_time()

    assert shown.offsetFromUtc() == zoneinfo_offset_now(DISAGREEING_ZONE)


def test_a_zone_qt_does_not_know_still_draws_a_time(qapp, tmp_path) -> None:
    window = _build_window(tmp_path)
    window._change_timezone(ZONE_QT_DOES_NOT_KNOW)

    shown = window._current_time()

    assert shown.isValid()
    assert shown.offsetFromUtc() == zoneinfo_offset_now(ZONE_QT_DOES_NOT_KNOW)
    assert window.time_zone_id == ZONE_QT_DOES_NOT_KNOW
