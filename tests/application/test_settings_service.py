"""SettingsService tests using a hand-written fake store."""

from __future__ import annotations

from typing import Any

from fancyclock.application.settings import (
    LOCALE_KEY,
    SKIN_NAME_KEY,
    TIMEZONE_ID_KEY,
    SettingsService,
)


class FakeStore:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any | None) -> None:
        if value is None:
            self.data.pop(key, None)
        else:
            self.data[key] = value


def test_skin_name_roundtrip_and_clear() -> None:
    store = FakeStore()
    service = SettingsService(store)

    assert service.skin_name() is None
    service.set_skin_name("waves")
    assert service.skin_name() == "waves"
    assert store.data[SKIN_NAME_KEY] == "waves"

    service.set_skin_name(None)
    assert service.skin_name() is None


def test_skin_name_ignores_non_string_values() -> None:
    store = FakeStore()
    store.data[SKIN_NAME_KEY] = 42
    assert SettingsService(store).skin_name() is None


def test_timezone_id_roundtrip_and_empty_is_none() -> None:
    store = FakeStore()
    service = SettingsService(store)

    assert service.timezone_id() is None
    service.set_timezone_id("Europe/London")
    assert service.timezone_id() == "Europe/London"
    assert store.data[TIMEZONE_ID_KEY] == "Europe/London"

    store.data[TIMEZONE_ID_KEY] = ""
    assert service.timezone_id() is None


def test_locale_roundtrip_and_empty_is_none() -> None:
    store = FakeStore()
    service = SettingsService(store)

    assert service.locale() is None
    service.set_locale("fr_FR")
    assert service.locale() == "fr_FR"
    assert store.data[LOCALE_KEY] == "fr_FR"

    store.data[LOCALE_KEY] = ""
    assert service.locale() is None
