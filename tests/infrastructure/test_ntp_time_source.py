"""NtpTimeSource tests against a real local UDP server."""

from __future__ import annotations

import socket
import struct
import threading
from datetime import datetime, timedelta, timezone

from fancyclock.infrastructure.ntp_time_source import (
    NTP_RESPONSE_FORMAT,
    NTP_TIMESTAMP_DELTA,
    TRANSMIT_SECONDS_INDEX,
    NtpTimeSource,
)

TEST_UNIX_TIMESTAMP = 1_700_000_000
TEST_TIMEOUT_SECONDS = 2.0
FALLBACK_TOLERANCE = timedelta(seconds=60)
NTP_FIELD_COUNT = 12


def _serve_one_datagram(payload_builder):
    """Start a one-shot local UDP server; return (port, thread)."""
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    port = server.getsockname()[1]

    def respond():
        try:
            data, addr = server.recvfrom(1024)
            server.sendto(payload_builder(data), addr)
        finally:
            server.close()

    thread = threading.Thread(target=respond, daemon=True)
    thread.start()
    return port, thread


def test_successful_query_returns_server_time() -> None:
    def build_response(_request: bytes) -> bytes:
        fields = [0] * NTP_FIELD_COUNT
        fields[TRANSMIT_SECONDS_INDEX] = TEST_UNIX_TIMESTAMP + NTP_TIMESTAMP_DELTA
        return struct.pack(NTP_RESPONSE_FORMAT, *fields)

    port, thread = _serve_one_datagram(build_response)
    source = NtpTimeSource(
        servers=("127.0.0.1",),
        port=port,
        timeout_seconds=TEST_TIMEOUT_SECONDS,
    )
    result = source.utc_time()
    thread.join(timeout=TEST_TIMEOUT_SECONDS)

    assert result == datetime.fromtimestamp(TEST_UNIX_TIMESTAMP, tz=timezone.utc)


def test_short_response_falls_back_to_system_clock() -> None:
    port, thread = _serve_one_datagram(lambda _request: b"tiny")
    source = NtpTimeSource(
        servers=("127.0.0.1",),
        port=port,
        timeout_seconds=TEST_TIMEOUT_SECONDS,
    )
    result = source.utc_time()
    thread.join(timeout=TEST_TIMEOUT_SECONDS)

    assert abs(result - datetime.now(timezone.utc)) < FALLBACK_TOLERANCE


def test_unreachable_server_falls_back_to_system_clock() -> None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    closed_port = probe.getsockname()[1]
    probe.close()

    source = NtpTimeSource(
        servers=("127.0.0.1",), port=closed_port, timeout_seconds=0.2
    )
    result = source.utc_time()

    assert abs(result - datetime.now(timezone.utc)) < FALLBACK_TOLERANCE
