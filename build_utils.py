#!/usr/bin/env python3
"""Shared shell helpers for the FancyClock build scripts."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# A git-LFS pointer file (an unresolved stub) begins with this signature line.
LFS_POINTER_MAGIC = b"version https://git-lfs.github.com/spec/v1"


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
            "Install git-lfs and run `git lfs pull` before building."
        )
