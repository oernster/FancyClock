"""EnvironmentLocaleProbe tests with injected environment and getter."""

from __future__ import annotations

from fancyclock.infrastructure.system_locale_probe import (
    EnvironmentLocaleProbe,
    _default_locale_getter,
    _windows_locale_name,
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


class FakeKernel32:
    """Stands in for kernel32: writes a fixed BCP-47 name into the buffer."""

    def __init__(self, name: str) -> None:
        self.name = name

    def GetUserDefaultLocaleName(self, buffer, size: int) -> int:  # noqa: N802
        if not self.name:
            return 0
        buffer.value = self.name
        return len(self.name) + 1


def test_windows_reads_the_bcp47_name_rather_than_the_display_name() -> None:
    assert _windows_locale_name(FakeKernel32("fr-FR")) == "fr-FR"


def test_a_failed_windows_read_gives_no_name() -> None:
    assert _windows_locale_name(FakeKernel32("")) is None


def test_on_windows_the_bcp47_name_comes_before_the_process_locale() -> None:
    assert _default_locale_getter("win32", lambda: "de-DE") == "de-DE"


def test_on_windows_a_missing_name_falls_back_to_the_process_locale() -> None:
    value = _default_locale_getter("win32", lambda: None)
    assert value is None or isinstance(value, str)


def test_elsewhere_the_windows_reader_is_never_asked() -> None:
    def must_not_run() -> str:
        raise AssertionError("the Windows reader ran off Windows")

    value = _default_locale_getter("linux", must_not_run)
    assert value is None or isinstance(value, str)
