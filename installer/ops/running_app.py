"""Detect whether FancyClock is currently running."""

from __future__ import annotations

from pathlib import Path

import psutil


def is_app_running(exe_path: Path) -> bool:
    exe_path = exe_path.resolve()
    for proc in psutil.process_iter(attrs=["exe"]):
        try:
            pexe = proc.info.get("exe")
            if not pexe:
                continue
            if Path(pexe).resolve() == exe_path:
                return True
        except (psutil.Error, OSError):
            # psutil.Error covers NoSuchProcess, AccessDenied and ZombieProcess;
            # resolving the executable path can raise OSError separately. A
            # process we cannot inspect is treated as not being ours, which is
            # the only safe reading: the alternative is refusing to install
            # because of some unrelated process.
            continue
    return False
