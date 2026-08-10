"""Tests for the update check's pure logic and service."""

from __future__ import annotations

import pytest

from fancyclock.application.ports import ReleaseAsset, ReleaseInfo
from fancyclock.application.update import (
    PLATFORM_KEY_LINUX,
    PLATFORM_KEY_MACOS,
    PLATFORM_KEY_WINDOWS,
    UpdateService,
    is_newer,
    platform_key_for,
    select_asset_url,
)

CURRENT = "2.2.0"


class FakeReleaseSource:
    def __init__(self, release: ReleaseInfo | None) -> None:
        self._release = release

    def latest_release(self) -> ReleaseInfo | None:
        return self._release


def release(
    version: str = "9.9.9", assets: tuple[ReleaseAsset, ...] | None = None
) -> ReleaseInfo:
    if assets is None:
        assets = (
            ReleaseAsset("FancyClockSetup.exe", "https://example.test/win"),
            ReleaseAsset("fancyclock.dmg", "https://example.test/mac"),
            ReleaseAsset("fancyclock.flatpak", "https://example.test/linux"),
        )
    return ReleaseInfo(
        version=version, page_url="https://example.test/rel", assets=assets
    )


class TestIsNewer:
    def test_newer_equal_and_older(self) -> None:
        assert is_newer("2.3.0", CURRENT) is True
        assert is_newer(CURRENT, CURRENT) is False
        assert is_newer("2.1.9", CURRENT) is False

    def test_prefix_and_whitespace_tolerated(self) -> None:
        assert is_newer("v2.3.0", CURRENT) is True
        assert is_newer("V2.3.0", CURRENT) is True
        assert is_newer("  2.3.0  ", CURRENT) is True

    def test_extra_component_compares_numerically(self) -> None:
        assert is_newer("2.2.0.1", CURRENT) is True
        assert is_newer("2.3", CURRENT) is True

    def test_malformed_is_never_newer(self) -> None:
        assert is_newer("not-a-version", CURRENT) is False
        assert is_newer("2.3.0", "garbage") is False
        assert is_newer("", CURRENT) is False

    def test_prerelease_suffix_is_never_newer(self) -> None:
        assert is_newer("2.3.0-rc1", CURRENT) is False


class TestPlatformKey:
    @pytest.mark.parametrize(
        ("sys_platform", "expected"),
        [
            ("win32", PLATFORM_KEY_WINDOWS),
            ("darwin", PLATFORM_KEY_MACOS),
            ("linux", PLATFORM_KEY_LINUX),
            ("freebsd14", PLATFORM_KEY_LINUX),
        ],
    )
    def test_mapping(self, sys_platform: str, expected: str) -> None:
        assert platform_key_for(sys_platform) == expected


class TestSelectAssetUrl:
    def test_picks_by_suffix_per_platform(self) -> None:
        assets = release().assets
        assert (
            select_asset_url(assets, PLATFORM_KEY_WINDOWS) == "https://example.test/win"
        )
        assert (
            select_asset_url(assets, PLATFORM_KEY_MACOS) == "https://example.test/mac"
        )
        assert (
            select_asset_url(assets, PLATFORM_KEY_LINUX) == "https://example.test/linux"
        )

    def test_suffix_match_is_case_insensitive(self) -> None:
        assets = (ReleaseAsset("Setup.EXE", "https://example.test/w"),)
        assert (
            select_asset_url(assets, PLATFORM_KEY_WINDOWS) == "https://example.test/w"
        )

    def test_no_match_and_unknown_key_return_none(self) -> None:
        assert select_asset_url((), PLATFORM_KEY_WINDOWS) is None
        assert select_asset_url(release().assets, "beos") is None


class TestUpdateService:
    def test_unreachable_source_returns_none(self) -> None:
        service = UpdateService(FakeReleaseSource(None), CURRENT, PLATFORM_KEY_WINDOWS)
        assert service.check() is None

    def test_newer_release_is_available_with_asset_and_page(self) -> None:
        service = UpdateService(
            FakeReleaseSource(release()), CURRENT, PLATFORM_KEY_WINDOWS
        )
        status = service.check()
        assert status is not None
        assert status.update_available is True
        assert status.latest == "9.9.9"
        assert status.current == CURRENT
        assert status.download_url == "https://example.test/win"
        assert status.page_url == "https://example.test/rel"

    def test_same_version_is_not_available(self) -> None:
        service = UpdateService(
            FakeReleaseSource(release(CURRENT)), CURRENT, PLATFORM_KEY_WINDOWS
        )
        status = service.check()
        assert status is not None
        assert status.update_available is False

    def test_skipped_version_is_seen_but_not_available(self) -> None:
        service = UpdateService(
            FakeReleaseSource(release()), CURRENT, PLATFORM_KEY_WINDOWS
        )
        status = service.check(skipped_version="9.9.9")
        assert status is not None
        assert status.update_available is False
        assert status.latest == "9.9.9"

    def test_different_skipped_version_still_prompts(self) -> None:
        service = UpdateService(
            FakeReleaseSource(release()), CURRENT, PLATFORM_KEY_WINDOWS
        )
        status = service.check(skipped_version="2.3.0")
        assert status is not None
        assert status.update_available is True

    def test_empty_assets_offer_no_download_url(self) -> None:
        service = UpdateService(
            FakeReleaseSource(release(assets=())), CURRENT, PLATFORM_KEY_WINDOWS
        )
        status = service.check()
        assert status is not None
        assert status.download_url is None
        assert status.page_url == "https://example.test/rel"
