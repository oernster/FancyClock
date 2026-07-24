"""EnvironmentLocaleProbe tests with injected environment and getter."""

from __future__ import annotations

from fancyclock.infrastructure.system_locale_probe import (
    EnvironmentLocaleProbe,
    _default_locale_getter,
)


def test_locale_getter_result_comes_first() -> None:
    probe = EnvironmentLocaleProbe(
        env={"LANG": "fr_FR.UTF-8"}, locale_getter=lambda: "en_GB"
    )
    assert probe.candidates() == ("en_GB", "fr_FR.UTF-8")


def test_env_priority_order_and_list_splitting() -> None:
    probe = EnvironmentLocaleProbe(
        env={
            "LANGUAGE": "de_DE:de",
            "LANG": "it_IT.UTF-8",
            "LC_ALL": "fr_FR.UTF-8",
        },
        locale_getter=lambda: None,
    )
    assert probe.candidates() == ("fr_FR.UTF-8", "it_IT.UTF-8", "de_DE")


def test_getter_failure_is_ignored() -> None:
    def broken() -> str:
        raise RuntimeError("no locale")

    probe = EnvironmentLocaleProbe(env={}, locale_getter=broken)
    assert probe.candidates() == ()


def test_default_env_is_process_environment() -> None:
    probe = EnvironmentLocaleProbe(locale_getter=lambda: "en_GB")
    assert probe.candidates()[0] == "en_GB"


def test_default_locale_getter_returns_str_or_none() -> None:
    value = _default_locale_getter()
    assert value is None or isinstance(value, str)
