"""Swapping a staged bundle into place; what happens when that fails.

Windows refuses to rename a folder that holds an open file, so holding one
open is a real way to make a rename fail. Where a failure needs a copy that
breaks part-way, a hand-written stand-in for ``shutil.copytree`` supplies it.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path

import pytest

from installer.ops import install_ops
from installer.ops.errors import InstallerOperationError
from installer.ops.install_ops import _swap_in_bundle


@pytest.fixture
def held() -> Iterator[ExitStack]:
    """Files a test holds open, all closed again before tmp_path cleanup."""
    with ExitStack() as stack:
        yield stack


def _folder(path: Path, name: str, text: str) -> Path:
    path.mkdir(parents=True)
    (path / name).write_text(text, encoding="utf-8")
    return path


def _backups(target: Path) -> list[Path]:
    return list(target.parent.glob(f"{target.name}.old.*"))


def test_swap_moves_staging_into_a_fresh_target(tmp_path: Path) -> None:
    staging = _folder(tmp_path / "staging", "new.txt", "new")
    target = tmp_path / "Programs" / "FancyClock"

    _swap_in_bundle(staging, target)

    assert (target / "new.txt").read_text(encoding="utf-8") == "new"
    assert not staging.exists()


def test_locked_existing_install_is_left_alone(tmp_path: Path, held: ExitStack) -> None:
    target = _folder(tmp_path / "FancyClock", "old.txt", "old")
    staging = _folder(tmp_path / "staging", "new.txt", "new")
    held.enter_context((target / "old.txt").open("rb"))

    with pytest.raises(InstallerOperationError, match="Unable to replace"):
        _swap_in_bundle(staging, target)

    assert (target / "old.txt").exists()
    assert (staging / "new.txt").exists()


def test_unmovable_staging_is_copied_instead(tmp_path: Path, held: ExitStack) -> None:
    staging = _folder(tmp_path / "staging", "new.txt", "new")
    held.enter_context((staging / "new.txt").open("rb"))
    target = tmp_path / "FancyClock"

    _swap_in_bundle(staging, target)

    assert (target / "new.txt").read_text(encoding="utf-8") == "new"


def _old_is_back(target: Path) -> None:
    assert sorted(p.name for p in target.iterdir()) == ["old.txt"]
    assert (target / "old.txt").read_text(encoding="utf-8") == "old"
    assert _backups(target) == []


def test_failed_swap_puts_the_previous_install_back(tmp_path: Path) -> None:
    target = _folder(tmp_path / "FancyClock", "old.txt", "old")

    with pytest.raises(InstallerOperationError, match="has been put back") as info:
        _swap_in_bundle(tmp_path / "no-staging", target)

    assert isinstance(info.value.__cause__, FileNotFoundError)
    _old_is_back(target)


def test_failed_fresh_swap_has_nothing_to_restore(tmp_path: Path) -> None:
    target = tmp_path / "FancyClock"

    with pytest.raises(InstallerOperationError, match="Nothing was installed"):
        _swap_in_bundle(tmp_path / "no-staging", target)

    assert not target.exists()


def test_copy_failing_part_way_keeps_the_previous_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = _folder(tmp_path / "FancyClock", "old.txt", "old")

    def copy_part_then_fail(src: Path, dst: Path, **kwargs: object) -> None:
        _folder(Path(dst), "partial.txt", "partial")
        raise shutil.Error("disk full part-way")

    monkeypatch.setattr(install_ops.shutil, "copytree", copy_part_then_fail)

    with pytest.raises(InstallerOperationError, match="disk full part-way") as info:
        _swap_in_bundle(tmp_path / "no-staging", target)

    assert "has been put back" in str(info.value)
    assert isinstance(info.value.__cause__, shutil.Error)
    _old_is_back(target)


def test_fresh_copy_failing_part_way_leaves_no_partial_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "FancyClock"

    def copy_part_then_fail(src: Path, dst: Path, **kwargs: object) -> None:
        _folder(Path(dst), "partial.txt", "partial")
        raise shutil.Error("disk full part-way")

    monkeypatch.setattr(install_ops.shutil, "copytree", copy_part_then_fail)

    with pytest.raises(InstallerOperationError, match="Nothing was installed"):
        _swap_in_bundle(tmp_path / "no-staging", target)

    assert not target.exists()


def test_any_failure_while_placing_restores_the_previous_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = _folder(tmp_path / "FancyClock", "old.txt", "old")

    def copy_then_break(src: Path, dst: Path, **kwargs: object) -> None:
        raise RuntimeError("not a filesystem error")

    monkeypatch.setattr(install_ops.shutil, "copytree", copy_then_break)

    with pytest.raises(InstallerOperationError, match="has been put back"):
        _swap_in_bundle(tmp_path / "no-staging", target)

    _old_is_back(target)


def test_refused_rollback_keeps_the_backup_and_names_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, held: ExitStack
) -> None:
    target = _folder(tmp_path / "FancyClock", "old.txt", "old")

    def copy_then_fail(src: Path, dst: Path, **kwargs: object) -> None:
        # Hold a file in the backup so the rollback rename is refused too.
        (backup,) = _backups(dst)
        held.enter_context((backup / "old.txt").open("rb"))
        raise OSError("copy failed")

    monkeypatch.setattr(install_ops.shutil, "copytree", copy_then_fail)

    with pytest.raises(InstallerOperationError, match="copy failed") as info:
        _swap_in_bundle(tmp_path / "no-staging", target)

    (backup,) = _backups(target)
    assert not target.exists()
    assert (backup / "old.txt").read_text(encoding="utf-8") == "old"
    assert str(backup) in str(info.value)
    assert f"Rename that folder to {target.name}" in str(info.value)


def test_unremovable_partial_install_keeps_the_backup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, held: ExitStack
) -> None:
    target = _folder(tmp_path / "FancyClock", "old.txt", "old")

    def copy_part_then_fail(src: Path, dst: Path, **kwargs: object) -> None:
        # Hold the partial file open so the partial folder cannot be removed
        # and the old install cannot be renamed back over it.
        partial = _folder(Path(dst), "partial.txt", "partial")
        held.enter_context((partial / "partial.txt").open("rb"))
        raise shutil.Error("disk full part-way")

    monkeypatch.setattr(install_ops.shutil, "copytree", copy_part_then_fail)

    with pytest.raises(InstallerOperationError, match="could not be moved back"):
        _swap_in_bundle(tmp_path / "no-staging", target)

    (backup,) = _backups(target)
    assert (backup / "old.txt").read_text(encoding="utf-8") == "old"


def test_backup_that_cannot_be_deleted_leaves_the_new_install_working(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, held: ExitStack
) -> None:
    target = _folder(tmp_path / "FancyClock", "old.txt", "old")
    staging = _folder(tmp_path / "staging", "new.txt", "new")
    held.enter_context((staging / "new.txt").open("rb"))
    real_copytree = shutil.copytree

    def copy_then_hold_backup(src: Path, dst: Path, **kwargs: object) -> None:
        real_copytree(src, dst, **kwargs)
        (backup,) = _backups(dst)
        held.enter_context((backup / "old.txt").open("rb"))

    monkeypatch.setattr(install_ops.shutil, "copytree", copy_then_hold_backup)

    _swap_in_bundle(staging, target)

    assert (target / "new.txt").read_text(encoding="utf-8") == "new"
    (backup,) = _backups(target)
    assert (backup / "old.txt").exists()


def test_successful_upgrade_removes_the_backup(tmp_path: Path) -> None:
    target = _folder(tmp_path / "FancyClock", "old.txt", "old")
    staging = _folder(tmp_path / "staging", "new.txt", "new")

    _swap_in_bundle(staging, target)

    assert sorted(p.name for p in target.iterdir()) == ["new.txt"]
    assert _backups(target) == []
