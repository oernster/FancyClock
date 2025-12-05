import PyInstaller.__main__
import sys
from pathlib import Path

def build_executable() -> None:
    """Build the Clock executable using PyInstaller, precisely replicating the audiodeck method."""
    project_root = Path(__file__).parent
    
    # Verify the required icon files exist, as they do in the reference project.
    if not (project_root / "clock.png").exists():
        print("ERROR: clock.png is missing.")
        sys.exit(1)
    if not (project_root / "clock.ico").exists():
        print("ERROR: clock.ico is missing.")
        sys.exit(1)

    # These arguments are a direct adaptation of the working audiodeck build script.
    args = [
        str(project_root / "main.py"),
        "--name=Clock",
        "--onefile",
        "--windowed",
        "--clean",
        f"--distpath={project_root / 'dist'}",
        f"--workpath={project_root / 'build'}",
        f"--specpath={project_root}",
        
        # The audiodeck script uses the .png for the --icon flag. I will do the same.
        "--icon=clock.png",
        
        # The audiodeck script bundles both icon files as data. I will do the same.
        f"--add-data={project_root / 'clock.ico'};.",
        f"--add-data={project_root / 'clock.png'};.",
        
        # Required hidden imports for PySide6.
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
    ]

    print("Building Clock executable using the exact audiodeck method...")
    PyInstaller.__main__.run(args)
    print("\nBuild complete!")

if __name__ == "__main__":
    build_executable()
