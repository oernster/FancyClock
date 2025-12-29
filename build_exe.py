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
    - Bundles the `media` directory so video skins are available at runtime.
    """
    project_root = Path(__file__).resolve().parent

    # Basic sanity checks
    main_py = project_root / "main.py"
    icon_png = project_root / "clock.png"
    icon_ico = project_root / "clock.ico"
    localization_dir = project_root / "localization"
    tz_locale_map = project_root / "timezone_locale_map.json"
    media_dir = project_root / "media"  # <-- includes video backgrounds
    license_file = project_root / "LICENSE"  # ⬅️ NEW

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
        print(
            "WARNING: timezone_locale_map.json is missing. "
            "Localization may not work as expected."
        )

    if not media_dir.exists():
        print(
            "WARNING: media/ directory is missing. " "Video skins will not be bundled."
        )

    if not license_file.exists():
        print("WARNING: LICENSE file is missing — it won't be bundled.")

    # PyInstaller uses ';' as separator on Windows and ':' on POSIX.
    data_sep = ";" if os.name == "nt" else ":"

    args = [
        str(main_py),
        "--name=FancyClock",
        "--onefile",
        "--windowed",
        "--clean",
        f"--distpath={project_root / 'dist'}",
        f"--workpath={project_root / 'build'}",
        f"--specpath={project_root}",
        f"--icon={icon_ico}",
        # Bundle icon files
        f"--add-data={icon_ico}{data_sep}.",
        f"--add-data={icon_png}{data_sep}.",
        # Bundle localization directory
        f"--add-data={localization_dir}{data_sep}localization",
        # Bundle timezone_locale_map.json
        f"--add-data={tz_locale_map}{data_sep}.",
        # ⬅️ NEW — Bundle the LICENSE file
        f"--add-data={license_file}{data_sep}.",
    ]

    # Bundle media directory (skins)
    if media_dir.exists():
        args.append(f"--add-data={media_dir}{data_sep}media")

    # Required hidden imports for PySide6
    args.extend(
        [
            "--hidden-import=PySide6.QtCore",
            "--hidden-import=PySide6.QtGui",
            "--hidden-import=PySide6.QtWidgets",
            "--hidden-import=PySide6.QtNetwork",
        ]
    )

    print("Building FancyClock executable...")
    print("PyInstaller arguments:\n  " + "\n  ".join(args))
    PyInstaller.__main__.run(args)
    print("\nBuild complete! EXE is in the 'dist' directory.")


if __name__ == "__main__":
    build_executable()
