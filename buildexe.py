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

# Third-party packages the app imports at runtime. A PyInstaller run from an
# environment missing one of these only WARNS (in the build warn file) and
# ships a broken exe, so we read that file and fail the build instead.
REQUIRED_BUNDLED_PACKAGES = ("PySide6", "pytz", "tzlocal")


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

    if spec_file.exists():
        spec_file.unlink()

    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    if build_dir.exists():
        shutil.rmtree(build_dir)

    # Always build with the interpreter running this script, so the analysed
    # environment is the venv that actually has the app's dependencies.
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
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
    if not exe_path.exists():
        print("EXE not found after build")
        return 1

    warn_file = build_dir / APP_NAME / f"warn-{APP_NAME}.txt"
    warn_text = warn_file.read_text(encoding="utf-8") if warn_file.exists() else ""
    missing = [
        name
        for name in REQUIRED_BUNDLED_PACKAGES
        if f"missing module named {name} -" in warn_text
    ]
    if missing:
        print(
            "Error: bundle is missing required packages: "
            + ", ".join(missing)
            + ". Check the environment running this build."
        )
        return 1

    print(f"[OK] EXE created: {exe_path}")
    print(f"Size: {exe_path.stat().st_size / (1024 * 1024):.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(build_exe())
