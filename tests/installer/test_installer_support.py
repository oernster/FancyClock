"""Payload access, resource paths, logging, the payload builder and the
licence lookup: the installer's supporting modules."""

from __future__ import annotations

import json
import logging
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest

from installer import build_payload as builder
from installer.ops import running_app
from installer.ops.payload import (
    iter_manifest_entries,
    load_manifest,
    manifest_json_path,
    payload_zip_path,
)
from installer.shared import logging_setup
from installer.shared.resource_path import bundled_data_root, resource_path
from installer.ui import lgpl3_license_text as lgpl
from tests.installer.installer_fakes import APP_FILES, Machine, stage_payload

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_manifest_and_zip_resolve_under_the_data_root(machine: Machine) -> None:
    stage_payload(machine.data_root, version="2.0.0")

    manifest = load_manifest()

    assert payload_zip_path().is_file()
    assert manifest_json_path().parent == payload_zip_path().parent
    assert manifest.installer_version == "2.0.0"
    assert [e.path for e in iter_manifest_entries(manifest)] == list(APP_FILES)


def test_manifest_without_fields_reads_as_empty(machine: Machine) -> None:
    stage_payload(machine.data_root)
    manifest_json_path().write_text("{}", encoding="utf-8")

    manifest = load_manifest()

    assert manifest.installer_version == ""
    assert manifest.entries == ()


def test_data_root_is_the_bundle_when_frozen(machine: Machine) -> None:
    assert bundled_data_root() == machine.data_root
    assert resource_path("a/b.txt") == machine.data_root / "a" / "b.txt"


def test_data_root_is_the_repository_from_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(sys, "_MEIPASS")

    assert bundled_data_root() == PROJECT_ROOT


def test_log_path_follows_local_app_data(machine: Machine) -> None:
    assert logging_setup.installer_log_path() == (
        machine.local / "FancyClockInstaller" / "logs" / "setup.log"
    )


def test_log_dir_falls_back_to_the_profile(
    machine: Machine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LOCALAPPDATA")

    assert logging_setup.installer_log_dir() == (
        machine.local / "FancyClockInstaller" / "logs"
    )


def test_setup_logging_writes_the_first_line(
    machine: Machine, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])
    monkeypatch.setattr(root, "level", root.level)

    log_path = logging_setup.setup_installer_logging()
    for handler in root.handlers:
        handler.close()

    assert log_path == logging_setup.installer_log_path()
    assert "Installer logging initialized" in log_path.read_text(encoding="utf-8")


@pytest.fixture
def bundle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the payload builder at a scratch bundle and output folder."""
    source = tmp_path / "dist" / "FancyClock"
    (source / "_internal" / "__pycache__").mkdir(parents=True)
    (source / "FancyClock.exe").write_bytes(APP_FILES["FancyClock.exe"])
    (source / "_internal" / "core.dll").write_bytes(APP_FILES["_internal/core.dll"])
    (source / "_internal" / "__pycache__" / "x.pyc").write_bytes(b"cache")
    out = tmp_path / "out"
    monkeypatch.setattr(builder, "SOURCE_BUNDLE_DIR", source)
    monkeypatch.setattr(builder, "PAYLOAD_DIR", out)
    monkeypatch.setattr(builder, "PAYLOAD_ZIP", out / "payload.zip")
    monkeypatch.setattr(builder, "MANIFEST_JSON", out / "manifest.json")
    return out


def test_build_payload_skips_caches_and_hashes_each_file(bundle: Path) -> None:
    builder.build_payload()

    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert [e["path"] for e in manifest["entries"]] == sorted(APP_FILES)
    assert manifest["installer_version"] == builder.__version__
    with zipfile.ZipFile(bundle / "payload.zip") as zf:
        assert sorted(zf.namelist()) == sorted(APP_FILES)
        assert zf.read("FancyClock.exe") == APP_FILES["FancyClock.exe"]


def test_build_payload_is_byte_for_byte_repeatable(bundle: Path) -> None:
    builder.build_payload()
    first = (bundle / "payload.zip").read_bytes()
    builder.build_payload()

    assert (bundle / "payload.zip").read_bytes() == first


def test_build_payload_refuses_a_missing_bundle(
    bundle: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(builder, "SOURCE_BUNDLE_DIR", tmp_path / "nowhere")

    with pytest.raises(SystemExit, match="Source bundle not found"):
        builder.build_payload()


def test_build_payload_refuses_to_run_off_windows(
    bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(builder, "os", SimpleNamespace(name="posix"))

    with pytest.raises(SystemExit, match="Windows builds"):
        builder.build_payload()


def test_licence_text_is_the_repository_licence() -> None:
    expected = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8", errors="replace")
    assert lgpl.LGPL_V3_TEXT == expected


def test_licence_prefers_the_frozen_bundle(machine: Machine) -> None:
    (machine.data_root / "LICENSE").write_text("bundled licence", encoding="utf-8")

    assert lgpl._read_lgpl3_text() == "bundled licence"


def test_licence_skips_a_directory_and_an_impossible_parent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delattr(sys, "_MEIPASS")
    (tmp_path / "LICENSE").mkdir()
    monkeypatch.setattr(lgpl, "sys", SimpleNamespace(executable=str(tmp_path / "x")))
    shallow = Path(tmp_path.anchor) / "module.py"
    monkeypatch.setattr(lgpl, "__file__", str(shallow))
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    (workdir / "LICENSE").write_text("working directory licence", encoding="utf-8")
    monkeypatch.chdir(workdir)

    assert lgpl._read_lgpl3_text() == "working directory licence"


class _UnreadablePath(type(Path())):
    """A path whose file exists but refuses to be read."""

    def read_text(self, *args: object, **kwargs: object) -> str:
        raise PermissionError(str(self))


def test_licence_lookup_reports_every_place_it_tried(
    machine: Machine, monkeypatch: pytest.MonkeyPatch
) -> None:
    (machine.data_root / "LICENSE").write_text("locked", encoding="utf-8")
    monkeypatch.setattr(lgpl, "Path", _UnreadablePath)

    with pytest.raises(FileNotFoundError, match="Unable to locate LICENSE"):
        lgpl._read_lgpl3_text()


def test_this_test_process_is_detected_as_running() -> None:
    assert running_app.is_app_running(Path(psutil.Process().exe()))


def test_an_absent_executable_is_not_running(tmp_path: Path) -> None:
    assert not running_app.is_app_running(tmp_path / "FancyClock.exe")


class _Proc:
    def __init__(self, exe: object) -> None:
        self._exe = exe

    @property
    def info(self) -> dict[str, object]:
        if isinstance(self._exe, Exception):
            raise self._exe
        return {"exe": self._exe}


def test_uninspectable_processes_are_not_ours(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "FancyClock.exe"
    processes = [
        _Proc(None),
        _Proc(psutil.AccessDenied()),
        _Proc(OSError("gone")),
        _Proc(str(tmp_path / "Other.exe")),
    ]
    monkeypatch.setattr(
        running_app.psutil, "process_iter", lambda attrs: iter(processes)
    )

    assert not running_app.is_app_running(target)
