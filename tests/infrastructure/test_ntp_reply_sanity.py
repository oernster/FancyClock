"""An NTP reply is checked before it is believed; a bad one moves on.

No socket is opened here. The exchange with each server is injected, so every
reply is a synthetic 48-byte packet built in the test and fed straight to the
parsing and sanity code.
"""

from __future__ import annotations

import struct
from datetime import datetime, timezone

from fancyclock.infrastructure.ntp_time_source import (
    NTP_PACKET_SIZE,
    NTP_RESPONSE_FORMAT,
    NTP_TIMESTAMP_DELTA,
    TRANSMIT_SECONDS_INDEX,
    NtpTimeSource,
    parse_ntp_reply,
)

NTP_FIELD_COUNT = 12
GOOD_UNIX_TIMESTAMP = 1_790_000_000
UNIX_1995 = 801_964_800
LEAP_NONE = 0
LEAP_UNSYNCHRONISED = 3
MODE_SERVER = 4
MODE_CLIENT = 3
VERSION = 4
STRATUM_PRIMARY = 1
STRATUM_KISS_OF_DEATH = 0
STRATUM_UNSYNCHRONISED = 16
HEADER_SHIFT = 24
STRATUM_SHIFT = 16
LEAP_SHIFT = 6
VERSION_SHIFT = 3


def reply(
    unix_seconds: int = GOOD_UNIX_TIMESTAMP,
    leap: int = LEAP_NONE,
    mode: int = MODE_SERVER,
    stratum: int = STRATUM_PRIMARY,
) -> bytes:
    """Build one 48-byte reply with the given header and transmit time."""
    fields = [0] * NTP_FIELD_COUNT
    first_byte = (leap << LEAP_SHIFT) | (VERSION << VERSION_SHIFT) | mode
    fields[0] = (first_byte << HEADER_SHIFT) | (stratum << STRATUM_SHIFT)
    if unix_seconds:
        fields[TRANSMIT_SECONDS_INDEX] = unix_seconds + NTP_TIMESTAMP_DELTA
    return struct.pack(NTP_RESPONSE_FORMAT, *fields)


class ScriptedExchange:
    """Answers each server with the reply the test scripted for it."""

    def __init__(self, replies: dict[str, bytes | None]) -> None:
        self.replies = replies
        self.asked: list[str] = []

    def __call__(self, server: str) -> bytes | None:
        self.asked.append(server)
        return self.replies[server]


def at(unix_seconds: int) -> datetime:
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)


def test_a_good_reply_parses_to_its_transmit_time() -> None:
    assert parse_ntp_reply(reply()) == GOOD_UNIX_TIMESTAMP


def test_an_all_zero_reply_is_refused() -> None:
    assert parse_ntp_reply(bytes(NTP_PACKET_SIZE)) is None


def test_an_unsynchronised_server_is_refused() -> None:
    assert parse_ntp_reply(reply(UNIX_1995, leap=LEAP_UNSYNCHRONISED)) is None


def test_a_kiss_of_death_stratum_is_refused() -> None:
    assert parse_ntp_reply(reply(stratum=STRATUM_KISS_OF_DEATH)) is None


def test_a_stratum_above_fifteen_is_refused() -> None:
    assert parse_ntp_reply(reply(stratum=STRATUM_UNSYNCHRONISED)) is None


def test_a_reply_that_is_not_from_a_server_is_refused() -> None:
    assert parse_ntp_reply(reply(mode=MODE_CLIENT)) is None


def test_a_zero_transmit_time_is_refused() -> None:
    assert parse_ntp_reply(reply(unix_seconds=0)) is None


def test_a_short_reply_is_refused() -> None:
    assert parse_ntp_reply(b"tiny") is None


def test_a_zero_reply_moves_on_to_the_next_server() -> None:
    exchange = ScriptedExchange({"bad": bytes(NTP_PACKET_SIZE), "good": reply()})
    source = NtpTimeSource(servers=("bad", "good"), exchange=exchange)
    assert source.utc_time() == at(GOOD_UNIX_TIMESTAMP)
    assert exchange.asked == ["bad", "good"]


def test_the_unsynchronised_1995_reply_never_sets_the_clock() -> None:
    bad = reply(UNIX_1995, leap=LEAP_UNSYNCHRONISED, stratum=STRATUM_KISS_OF_DEATH)
    exchange = ScriptedExchange({"bad": bad, "good": reply()})
    source = NtpTimeSource(servers=("bad", "good"), exchange=exchange)
    assert source.utc_time() == at(GOOD_UNIX_TIMESTAMP)


def test_a_timestamp_the_platform_cannot_convert_moves_on(monkeypatch) -> None:
    exchange = ScriptedExchange({"odd": reply(), "good": reply()})
    source = NtpTimeSource(servers=("odd", "good"), exchange=exchange)
    real_convert = source._to_datetime
    calls = []

    def convert_failing_once(timestamp: float):
        calls.append(timestamp)
        if len(calls) == 1:
            raise OSError("Invalid argument")
        return real_convert(timestamp)

    monkeypatch.setattr(source, "_to_datetime", convert_failing_once)
    assert source.utc_time() == at(GOOD_UNIX_TIMESTAMP)
    assert exchange.asked == ["odd", "good"]


def test_no_usable_reply_falls_back_to_the_system_clock() -> None:
    exchange = ScriptedExchange({"silent": None, "zero": bytes(NTP_PACKET_SIZE)})
    source = NtpTimeSource(servers=("silent", "zero"), exchange=exchange)
    before = datetime.now(timezone.utc)
    result = source.utc_time()
    assert before <= result <= datetime.now(timezone.utc)
