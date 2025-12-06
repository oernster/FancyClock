import os
import sys
from pathlib import Path

import PyInstaller.__main__


def build_executable() -> None:
    """
    Build the FancyClock executable using PyInstaller.

    Key points:
    - Uses clock.ico as the Windows EXE icon.
    - Bundles clock.png and clock.ico as data.
    - Bundles the entire `localization` directory so translations work
      when running from the EXE.
    - Bundles timezone_locale_map.json used by the localization layer.
    """
    project_root = Path(__file__).resolve().parent

    # Basic sanity checks
    main_py = project_root / "main.py"
    icon_png = project_root / "clock.png"
    icon_ico = project_root / "clock.ico"
    localization_dir = project_root / "localization"
    tz_locale_map = project_root / "timezone_locale_map.json"

    if not main_py.exists():
        print("ERROR: main.py is missing next to build_exe.py.")
        sys.exit(1)

    if not icon_png.exists():
        print("ERROR: clock.png is missing.")
        sys.exit(1)

    if not icon_ico.exists():
        print("ERROR: clock.ico is missing.")
        sys.exit(1)

    if not localization_dir.exists():
        print("ERROR: localization/ directory is missing.")
        sys.exit(1)

    if not tz_locale_map.exists():
        print("WARNING: timezone_locale_map.json is missing. "
              "Localization may not work as expected.")

    # PyInstaller uses ';' as the separator on Windows and ':' on POSIX.
    data_sep = ";" if os.name == "nt" else ":"

    args = [
        str(main_py),

        # EXE name (file will be FancyClock.exe on Windows)
        "--name=FancyClock",

        "--onefile",
        "--windowed",
        "--clean",

        f"--distpath={project_root / 'dist'}",
        f"--workpath={project_root / 'build'}",
        f"--specpath={project_root}",

        # Use the .ico for the EXE icon on Windows (no Pillow needed).
        f"--icon={icon_ico}",

        # Bundle icon files as data so the app can still load them at runtime.
        f"--add-data={icon_ico}{data_sep}.",
        f"--add-data={icon_png}{data_sep}.",

        # 🔥 IMPORTANT: bundle localization so translations work inside the EXE.
        f"--add-data={localization_dir}{data_sep}localization",

        # Bundle timezone_locale_map.json (used by localization / timezone code).
        f"--add-data={tz_locale_map}{data_sep}.",

        # Required hidden imports for PySide6.
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtNetwork",
    ]

    print("Building FancyClock executable...")
    print("PyInstaller arguments:\n  " + "\n  ".join(args))
    PyInstaller.__main__.run(args)
    print("\nBuild complete! EXE is in the 'dist' directory.")


if __name__ == "__main__":
    build_executable()
