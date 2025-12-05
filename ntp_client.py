import ntplib
from datetime import datetime, timezone

class NTPClient:
    def __init__(self, servers=None, timeout=5):
        if servers is None:
            self.servers = ["pool.ntp.org", "time.google.com", "time.windows.com"]
        else:
            self.servers = servers
        self.timeout = timeout
        self.client = ntplib.NTPClient()
        self._last_successful_server = None

    def get_time(self):
        if self._last_successful_server:
            result = self._try_server_sync(self._last_successful_server)
            if result:
                return result

        for server in self.servers:
            if server == self._last_successful_server:
                continue

            result = self._try_server_sync(server)
            if result:
                self._last_successful_server = server
                return result
        
        print("All NTP servers failed. Falling back to local time.")
        return datetime.now(timezone.utc)

    def _try_server_sync(self, server):
        try:
            response = self.client.request(server, version=3, timeout=self.timeout)
            return datetime.fromtimestamp(response.tx_time, timezone.utc)
        except Exception as e:
            print(f"Error getting NTP time from {server}: {e}")
            return None