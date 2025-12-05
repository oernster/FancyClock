import socket
import struct
import time
from datetime import datetime, timezone


class NTPClient:
    SERVERS = [
        "0.pool.ntp.org",
        "1.pool.ntp.org",
        "2.pool.ntp.org",
        "pool.ntp.org",
    ]

    def get_time(self):
        """
        Return the best available time:
        - Tries multiple NTP servers (with very short timeout)
        - Falls back to system UTC time on any error
        Never throws exceptions.
        """

        for server in self.SERVERS:
            try:
                t = self._query_server(server)
                if t is not None:
                    return datetime.fromtimestamp(t, tz=timezone.utc)
            except Exception:
                pass

        # Fallback: system clock in UTC
        return datetime.now(timezone.utc)

    def _query_server(self, server):
        """
        Query a single NTP server.
        Returns: timestamp (float) or None
        """

        NTP_TIMESTAMP_DELTA = 2208988800
        port = 123
        timeout = 0.8     # keep VERY short to avoid UI hangs

        msg = b'\x1b' + 47 * b'\0'

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(timeout)
                s.sendto(msg, (server, port))
                data, _ = s.recvfrom(1024)
        except Exception:
            return None

        if len(data) < 48:
            return None

        # Unpack NTP response
        unpacked = struct.unpack("!12I", data)
        transmit_timestamp = unpacked[10] + float(unpacked[11]) / 2**32

        # Convert NTP → Unix epoch
        return transmit_timestamp - NTP_TIMESTAMP_DELTA
