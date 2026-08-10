"""Tests for the GitHub releases adapter, with the opener faked."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from fancyclock.infrastructure.github_release_source import (
    ACCEPT_HEADER,
    RELEASES_LATEST_URL,
    REQUEST_TIMEOUT_SECONDS,
    GitHubReleaseSource,
)


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class FakeOpener:
    def __init__(self, body: bytes | None = None, error: Exception | None = None):
        self._body = body
        self._error = error
        self.request: urllib.request.Request | None = None
        self.timeout: float | None = None

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        self.request = request
        self.timeout = timeout
        if self._error is not None:
            raise self._error
        return FakeResponse(self._body or b"")


def payload(**overrides: Any) -> bytes:
    data: dict[str, Any] = {
        "tag_name": "v2.3.0",
        "html_url": "https://example.test/rel",
        "assets": [
            {
                "name": "FancyClockSetup.exe",
                "browser_download_url": "https://example.test/win",
            }
        ],
    }
    data.update(overrides)
    return json.dumps(data).encode("utf-8")


def test_happy_path_parses_release_and_strips_v() -> None:
    source = GitHubReleaseSource(opener=FakeOpener(payload()))
    release = source.latest_release()
    assert release is not None
    assert release.version == "2.3.0"
    assert release.page_url == "https://example.test/rel"
    assert release.assets[0].name == "FancyClockSetup.exe"
    assert release.assets[0].download_url == "https://example.test/win"


def test_request_targets_the_endpoint_with_header_and_timeout() -> None:
    opener = FakeOpener(payload())
    GitHubReleaseSource(opener=opener).latest_release()
    assert opener.request is not None
    assert opener.request.full_url == RELEASES_LATEST_URL
    assert opener.request.get_header("Accept") == ACCEPT_HEADER
    assert opener.timeout == REQUEST_TIMEOUT_SECONDS


def test_network_error_reads_as_no_release() -> None:
    source = GitHubReleaseSource(opener=FakeOpener(error=OSError("down")))
    assert source.latest_release() is None


def test_unparseable_body_reads_as_no_release() -> None:
    source = GitHubReleaseSource(opener=FakeOpener(b"not json"))
    assert source.latest_release() is None


def test_non_dict_body_reads_as_no_release() -> None:
    source = GitHubReleaseSource(opener=FakeOpener(b"[1, 2]"))
    assert source.latest_release() is None


def test_missing_or_wrong_typed_fields_read_as_no_release() -> None:
    for override in (
        {"tag_name": None},
        {"tag_name": ""},
        {"tag_name": 7},
        {"html_url": None},
        {"html_url": ""},
        {"html_url": 7},
    ):
        source = GitHubReleaseSource(opener=FakeOpener(payload(**override)))
        assert source.latest_release() is None, override


def test_malformed_assets_are_filtered_not_fatal() -> None:
    body = payload(
        assets=[
            "not a dict",
            {"name": "", "browser_download_url": "https://example.test/x"},
            {"name": "ok.dmg"},
            {"name": "good.flatpak", "browser_download_url": "https://example.test/l"},
        ]
    )
    release = GitHubReleaseSource(opener=FakeOpener(body)).latest_release()
    assert release is not None
    assert [asset.name for asset in release.assets] == ["good.flatpak"]


def test_assets_absent_or_non_list_read_as_empty() -> None:
    for override in ({"assets": None}, {"assets": "nope"}):
        release = GitHubReleaseSource(
            opener=FakeOpener(payload(**override))
        ).latest_release()
        assert release is not None
        assert release.assets == ()


def test_default_opener_is_urlopen(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> Any:
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse(payload())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    release = GitHubReleaseSource().latest_release()
    assert release is not None
    assert captured["url"] == RELEASES_LATEST_URL
    assert captured["timeout"] == REQUEST_TIMEOUT_SECONDS
