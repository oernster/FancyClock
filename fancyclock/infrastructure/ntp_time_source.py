"""NTP implementation of the TimeSource port.

Queries a short list of public NTP servers with a very short timeout so the
UI never hangs, falling back to the system clock when nothing answers.
"""

from __future__ import annotations

import socket
import struct
from datetime import datetime, timezone

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


class NtpTimeSource:
    """Fetches UTC time over NTP with a system-clock fallback."""

    def __init__(
        self,
        servers: tuple[str, ...] = DEFAULT_SERVERS,
        port: int = NTP_PORT,
        timeout_seconds: float = QUERY_TIMEOUT_SECONDS,
    ) -> None:
        self._servers = servers
        self._port = port
        self._timeout_seconds = timeout_seconds

    def utc_time(self) -> datetime:
        """Return the best available UTC time; never raises."""
        for server in self._servers:
            timestamp = self._query_server(server)
            if timestamp is not None:
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return datetime.now(timezone.utc)

    def _query_server(self, server: str) -> float | None:
        """Query one NTP server; return a Unix timestamp or ``None``."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self._timeout_seconds)
                sock.sendto(NTP_REQUEST, (server, self._port))
                data, _ = sock.recvfrom(RECEIVE_BUFFER_SIZE)
        except Exception:
            return None

        if len(data) < NTP_PACKET_SIZE:
            return None

        unpacked = struct.unpack(NTP_RESPONSE_FORMAT, data[:NTP_PACKET_SIZE])
        transmit_timestamp = (
            unpacked[TRANSMIT_SECONDS_INDEX]
            + float(unpacked[TRANSMIT_FRACTION_INDEX]) / FRACTION_DENOMINATOR
        )
        return transmit_timestamp - NTP_TIMESTAMP_DELTA
