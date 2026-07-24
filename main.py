# Import the composition root directly (not via the package's lazy
# __getattr__) so PyInstaller's static analysis follows the full import
# graph, including third-party dependencies.
from fancyclock.main import main

if __name__ == "__main__":
    raise SystemExit(main())
