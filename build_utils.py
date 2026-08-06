#!/usr/bin/env python3
"""Shared shell helpers for the FancyClock build scripts."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# A git-LFS pointer file (an unresolved stub) begins with this signature line.
LFS_POINTER_MAGIC = b"version https://git-lfs.github.com/spec/v1"

CLEAR_TREE_ATTEMPTS = 50
CLEAR_TREE_WAIT_SECONDS = 0.1


def clear_tree(path: Path) -> None:
    """Remove a directory tree so its path is immediately reusable.

    A plain rmtree can return while an antivirus or indexer handle keeps
    the tree in a delete-pending state; a directory recreated on that
    path silently dies with it. That intermittently broke installer
    builds (PyInstaller's fresh work directory vanished mid-write) and
    once took a finished app bundle with it. Renaming the tree aside
    frees the path atomically; the renamed tree is then deleted and the
    original path confirmed gone before returning.
    """
    for stale in path.parent.glob(f"{path.name}.doomed-*"):
        shutil.rmtree(stale, ignore_errors=True)
    if not path.exists():
        return
    doomed = path.with_name(f"{path.name}.doomed-{os.getpid()}")
    try:
        os.rename(path, doomed)
    except OSError:
        doomed = path
    shutil.rmtree(doomed, ignore_errors=True)
    for _ in range(CLEAR_TREE_ATTEMPTS):
        if not path.exists():
            return
        time.sleep(CLEAR_TREE_WAIT_SECONDS)
    raise SystemExit(f"Unable to clear directory: {path}")


def run(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, check=check, **kwargs)


def require(tool: str, brew_pkg: str | None = None) -> None:
    if shutil.which(tool):
        return
    pkg = brew_pkg or tool
    print(f"{tool} not found: installing via brew...")
    run(["brew", "install", pkg])
    if not shutil.which(tool):
        sys.exit(f"ERROR: {tool} still not found after brew install. Aborting.")


def _module_importable(module: str) -> bool:
    return (
        subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            capture_output=True,
        ).returncode
        == 0
    )


def require_module(module: str, pip_pkg: str | None = None) -> None:
    """Ensure a Python module is importable by the CURRENT interpreter.

    The build invokes PyInstaller as ``sys.executable -m PyInstaller``, so a
    ``pyinstaller`` executable elsewhere on PATH (e.g. a Homebrew install) does
    not prove the venv running this build can import it. Check and install
    against the same interpreter the build actually uses.
    """
    if _module_importable(module):
        return
    pkg = pip_pkg or module
    print(f"{module} not importable by {sys.executable}: installing via pip...")
    run([sys.executable, "-m", "pip", "install", pkg])
    if not _module_importable(module):
        sys.exit(f"ERROR: {module} still not importable after pip install. Aborting.")


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def lfs_pointer_stubs(root: Path) -> list[Path]:
    """Return files under ``root`` that are unresolved git-LFS pointer stubs.

    An LFS-tracked file that was checked out without git-lfs present is left as
    a small text pointer rather than the real content. Packaging it silently
    ships a broken asset, so builds check for these before bundling.
    """
    stubs: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            with path.open("rb") as handle:
                head = handle.read(len(LFS_POINTER_MAGIC))
        except OSError:
            continue
        if head == LFS_POINTER_MAGIC:
            stubs.append(path)
    return stubs


def require_materialized(root: Path) -> None:
    """Abort the build if any asset under ``root`` is an unresolved LFS stub."""
    stubs = lfs_pointer_stubs(root)
    if stubs:
        names = ", ".join(str(p) for p in stubs)
        sys.exit(
            f"ERROR: git-LFS content not materialized: {names}. "
            "Run `git lfs install` (registers the smudge filters, needed once "
            "per machine even when git-lfs is on PATH) then `git lfs fetch "
            "--all` and `git lfs checkout` before building."
        )
