"""Build the standalone FancyClock EXE bundle with PyInstaller."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import stamp_version

APP_NAME = "FancyClock"
ENTRYPOINT = "main.py"
ICON = "assets/fancyclock.ico"
DIST_DIR_NAME = "dist-pyinstaller"

# (source, destination) pairs shipped as data. resource_path() resolves these
# relative to the bundle data root at runtime.
DATA_DIRS = (
    ("localization", "localization"),
    ("media", "media"),
    ("assets", "assets"),
)
DATA_FILES = (
    "timezone_locale_map.json",
    "VERSION",
    "LICENSE",
)


def build_exe() -> int:
    """Create the onedir bundle wrapped later by buildinstaller.py."""
    print(f"Building {APP_NAME} EXE...")

    # Propagate the canonical VERSION into static docs before packaging, so a
    # release never ships docs whose version disagrees with VERSION.
    stamp_version.main()

    root = Path(__file__).parent
    dist_dir = root / DIST_DIR_NAME
    build_dir = root / "build"
    spec_file = root / f"{APP_NAME}.spec"

    pyinstaller_exe = shutil.which("pyinstaller")
    if not pyinstaller_exe:
        print(
            "Error: pyinstaller not found. "
            "Activate the venv and install requirements-dev.txt"
        )
        return 1

    if spec_file.exists():
        spec_file.unlink()

    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    if build_dir.exists():
        shutil.rmtree(build_dir)

    cmd = [
        pyinstaller_exe,
        f"--name={APP_NAME}",
        "--onedir",
        "--windowed",
        f"--icon={ICON}",
        "--noconfirm",
        f"--distpath={DIST_DIR_NAME}",
    ]
    for src, dest in DATA_DIRS:
        cmd.append(f"--add-data={src}{os.pathsep}{dest}")
    for src in DATA_FILES:
        cmd.append(f"--add-data={src}{os.pathsep}.")
    cmd.append(ENTRYPOINT)

    result = subprocess.run(cmd, cwd=root)
    if result.returncode != 0:
        print("PyInstaller build failed")
        return 1

    exe_path = dist_dir / APP_NAME / f"{APP_NAME}.exe"
    if exe_path.exists():
        print(f"[OK] EXE created: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / (1024 * 1024):.1f} MB")
        return 0

    print("EXE not found after build")
    return 1


if __name__ == "__main__":
    sys.exit(build_exe())
