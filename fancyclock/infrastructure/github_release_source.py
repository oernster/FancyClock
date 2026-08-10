"""GitHub releases adapter for the update check's ReleaseSource port.

Queries the ``releases/latest`` endpoint, which by contract returns only a
published, non-draft, non-prerelease release: a tag pushed mid-development
is structurally invisible, so it can never prompt. The request is
anonymous and any failure reads as "no release visible".
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Callable

from fancyclock.application.ports import ReleaseAsset, ReleaseInfo

RELEASES_LATEST_URL = "https://api.github.com/repos/oernster/FancyClock/releases/latest"
ACCEPT_HEADER = "application/vnd.github+json"
REQUEST_TIMEOUT_SECONDS = 5.0


def _default_opener(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310


def _parse_assets(raw: Any) -> tuple[ReleaseAsset, ...]:
    """Return the well-formed assets, silently dropping malformed entries."""
    if not isinstance(raw, list):
        return ()
    assets = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        url = entry.get("browser_download_url")
        if isinstance(name, str) and name and isinstance(url, str) and url:
            assets.append(ReleaseAsset(name=name, download_url=url))
    return tuple(assets)


class GitHubReleaseSource:
    """Implements ReleaseSource over stdlib urllib.

    The opener is injected so tests never touch the network.
    """

    def __init__(
        self,
        opener: Callable[[urllib.request.Request, float], Any] = _default_opener,
    ) -> None:
        self._opener = opener

    def latest_release(self) -> ReleaseInfo | None:
        """Return the latest published release, else ``None`` on any failure."""
        request = urllib.request.Request(
            RELEASES_LATEST_URL, headers={"Accept": ACCEPT_HEADER}
        )
        try:
            with self._opener(request, REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError):
            # Offline, refused, rate-limited or unparseable: every one of
            # these means the same thing to the caller, no release visible.
            return None
        if not isinstance(payload, dict):
            return None
        tag = payload.get("tag_name")
        page_url = payload.get("html_url")
        if not isinstance(tag, str) or not tag:
            return None
        if not isinstance(page_url, str) or not page_url:
            return None
        version = tag[1:] if tag[:1] in ("v", "V") else tag
        return ReleaseInfo(
            version=version,
            page_url=page_url,
            assets=_parse_assets(payload.get("assets")),
        )
