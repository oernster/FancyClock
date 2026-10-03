"""NTP implementation of the TimeSource port.

Queries a short list of public NTP servers with a very short timeout so the
UI never hangs, falling back to the system clock when nothing answers.
"""

from __future__ import annotations

import socket
import struct
from datetime import datetime, timezone
from typing import Callable

DEFAULT_SERVERS: tuple[str, ...] = (
    "0.pool.ntp.org",
    "1.pool.ntp.org",
    "2.pool.ntp.org",
    "pool.ntp.org",
)
NTP_PORT = 123
QUERY_TIMEOUT_SECONDS = 0.8
NTP_TIMESTAMP_DELTA = 2208988800
NTP_PACKET_SIZE = 48
NTP_RESPONSE_FORMAT = "!12I"
TRANSMIT_SECONDS_INDEX = 10
TRANSMIT_FRACTION_INDEX = 11
FRACTION_DENOMINATOR = 2**32
NTP_REQUEST = b"\x1b" + (NTP_PACKET_SIZE - 1) * b"\0"
RECEIVE_BUFFER_SIZE = 1024

# Reply header fields (RFC 5905, section 7.3).
HEADER_BYTE_INDEX = 0
STRATUM_BYTE_INDEX = 1
LEAP_SHIFT = 6
MODE_MASK = 0b111
LEAP_UNSYNCHRONISED = 3
MODE_SERVER = 4
MIN_STRATUM = 1
MAX_STRATUM = 15


def parse_ntp_reply(data: bytes) -> float | None:
    """Return the Unix transmit time a reply states; ``None`` if unusable.

    A reply is believed only when it says it is a synchronised server answer
    (RFC 5905): the leap indicator is not "unsynchronised", the mode is
    "server", the stratum is a real one (a stratum of 0 is a Kiss-o'-Death
    refusal; above 15 means unsynchronised) and a transmit time is present.
    """
    if len(data) < NTP_PACKET_SIZE:
        return None
    first_byte = data[HEADER_BYTE_INDEX]
    leap = first_byte >> LEAP_SHIFT
    mode = first_byte & MODE_MASK
    stratum = data[STRATUM_BYTE_INDEX]
    if leap == LEAP_UNSYNCHRONISED or mode != MODE_SERVER:
        return None
    if not MIN_STRATUM <= stratum <= MAX_STRATUM:
        return None
    unpacked = struct.unpack(NTP_RESPONSE_FORMAT, data[:NTP_PACKET_SIZE])
    if not (unpacked[TRANSMIT_SECONDS_INDEX] or unpacked[TRANSMIT_FRACTION_INDEX]):
        return None
    transmit_timestamp = (
        unpacked[TRANSMIT_SECONDS_INDEX]
        + float(unpacked[TRANSMIT_FRACTION_INDEX]) / FRACTION_DENOMINATOR
    )
    return transmit_timestamp - NTP_TIMESTAMP_DELTA


class NtpTimeSource:
    """Fetches UTC time over NTP with a system-clock fallback."""

    def __init__(
        self,
        servers: tuple[str, ...] = DEFAULT_SERVERS,
        port: int = NTP_PORT,
        timeout_seconds: float = QUERY_TIMEOUT_SECONDS,
        exchange: Callable[[str], bytes | None] | None = None,
    ) -> None:
        self._servers = servers
        self._port = port
        self._timeout_seconds = timeout_seconds
        self._exchange = exchange if exchange is not None else self._udp_exchange

    def utc_time(self) -> datetime:
        """Return the best available UTC time; never raises."""
        for server in self._servers:
            data = self._exchange(server)
            timestamp = parse_ntp_reply(data) if data is not None else None
            if timestamp is None:
                continue
            try:
                return self._to_datetime(timestamp)
            except (OverflowError, OSError, ValueError):
                # A time this platform cannot represent: this server's answer
                # is unusable, so the next server is asked instead.
                continue
        return datetime.now(timezone.utc)

    @staticmethod
    def _to_datetime(timestamp: float) -> datetime:
        """Convert a Unix timestamp to an aware UTC datetime."""
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def _udp_exchange(self, server: str) -> bytes | None:
        """Send one request to ``server``; return the raw reply or ``None``."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self._timeout_seconds)
                sock.sendto(NTP_REQUEST, (server, self._port))
                data, _ = sock.recvfrom(RECEIVE_BUFFER_SIZE)
        except Exception:  # noqa: BLE001
            # Falls back to None, which makes the caller try the next
            # server and then the system clock. A time server is reached
            # over a network that can fail in ways no exception list
            # predicts. A clock must start whether or not it is reachable.
            return None
        return data
