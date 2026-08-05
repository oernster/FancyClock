# Development Notes

The single developer guide for this repository: everything needed to clone it,
run the test suite and produce a package on any of the three platforms. There is
no second development document; if a build note belongs anywhere, it belongs
here.

For the shape of the code itself (layers, invariants and the tests that enforce
them) see [`ARCHITECTURE.md`](ARCHITECTURE.md). For what is still open see
[`TECH_DEBT.md`](TECH_DEBT.md).

## 1. Clone and Git LFS

The animated backgrounds under `media/` are tracked with **Git LFS**. Without
LFS the `.mp4` files arrive as small pointer stubs and every video skin fails to
play, usually with "moov atom not found".

Install Git LFS for your platform:

```bash
sudo apt install git-lfs      # Ubuntu, Debian, Mint, Pop_OS
sudo dnf install git-lfs      # Fedora
sudo pacman -S git-lfs        # Arch, Manjaro
```

On Windows and macOS, LFS ships with Git for Windows and with Homebrew's `git`
respectively; `winget install GitHub.GitLFS` or `brew install git-lfs` also work.

Then, once per machine and once per clone:

```bash
git lfs install
git lfs fetch --all
git lfs checkout
```

Verify the media are real files rather than pointers:

```bash
ls -lh media/*.mp4    # megabytes, not ~130 bytes
```

## 2. Python environment

Python 3.11 or newer. Create a virtual environment and install both requirement
sets:

```bash
python -m venv venv
source venv/bin/activate          # Windows PowerShell: venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

Run the app from the repo root:

```bash
python main.py
```

## 3. Tests and quality checks

```bash
python -m pytest
python -m black --check .
python -m flake8 .
python -m ruff check .
```

`pytest` carries a hard 100% coverage gate over the domain, application and
infrastructure layers (see `.coveragerc` for the measured surface) plus
structural tests that enforce the architecture. A coverage-gated run prints the
coverage table last, so read the exit code rather than the tail of the output.

## 4. Build entry points

| Target | Command | Output |
|---|---|---|
| Windows app bundle | `python buildexe.py` | `dist-pyinstaller/FancyClock/` |
| Windows installer | `python buildinstaller.py` | `dist-installer/FancyClockSetup.exe` |
| macOS DMG (run on a Mac) | `python builddmg.py` | `fancyclock-macos-<arch>.dmg` |
| Linux Flatpak | `./build_flatpak.sh` | `dist/FancyClock.flatpak` |
| Icon assets | `python generate_icons.py` | badged `fancyclock.png` plus `assets/` from the `fancyclock_plain.png` master |
| Alarm sounds | `python generate_sounds.py` | `assets/sounds/` (deterministic stdlib synthesis) |

### Version stamping

`VERSION` at the repo root is the single source of truth. The runtime reads it
through `fancyclock.version`, packaging reads it through the dynamic version in
`pyproject.toml` and the build scripts read it through
`stamp_version.read_version()`.

The gh-pages site under `docs/` is served as static files and cannot read
`VERSION` at render time, so `stamp_version.py` writes the current version into
it. `buildexe.py`, `buildinstaller.py` and `builddmg.py` all call it before
packaging; run `python stamp_version.py` directly after a version bump if you
want the site current before a build. It touches `docs/` only and never the
markdown at the repo root.

## 5. Flatpak

The Flatpak build is **offline** for Python dependencies: every wheel and sdist
must be pre-populated into a local `vendor/` directory before the build runs.

### 5.1 Runtime prerequisites

FancyClock builds against KDE Runtime 6.8. One-time setup:

```bash
flatpak install flathub org.kde.Sdk//6.8
flatpak install flathub org.kde.Platform//6.8
```

These provide Python 3.12 inside the sandbox, the Qt 6 frameworks, the ffmpeg
backend that plays the video skins and the SDK tools needed to build krb5.

### 5.2 Generate `vendor/`

The manifest installs dependencies with
`python3 -m pip install --no-index --find-links=vendor --prefix=/app -r requirements.txt`,
so everything must exist locally. Rebuild from scratch:

```bash
rm -rf vendor
mkdir -p vendor
pip download -r requirements.txt -d vendor
```

The Flatpak runtime uses Python 3.12, so run the download with a Python whose
wheels are compatible (or pass `--python-version 3.12`). Afterwards `vendor/`
should hold the PySide6, shiboken6, pyside6-addons and pyside6-essentials
wheels plus `pytz`, `tzlocal` and `tzdata` (the IANA data behind `zoneinfo`,
which alarm scheduling depends on).

### 5.3 krb5

QtMultimedia needs `libgssapi_krb5.so.2`. The manifest at
[`uk.codecrafter.FancyClock.yml`](uk.codecrafter.FancyClock.yml) builds it as an
embedded `krb5` module, so there is nothing to install by hand.

### 5.4 Build

Before running the build, confirm the LFS assets are real files, `vendor/` is
populated and the Flatpak runtimes are installed. Then:

```bash
./build_flatpak.sh --user
```

The script builds krb5 in the sandbox, installs the wheels from `vendor/`,
copies the app files, media, translations and `LICENSE`, then packages and
installs the result. Run it without flags in an interactive terminal and it
prompts for the install scope; choose the system option and it prints the exact
`sudo flatpak install --system ...` command and offers to run it.

Outputs are the bundle at `dist/FancyClock.flatpak` and a local OSTree repo at
`dist/repo`.

**No Flathub, offline by default:** the script installs with
`flatpak install --bundle --no-deps --no-related`, which stops Flatpak reaching
for `flathub` or any other remote during the install step. To disable those
flags, only worth doing when you have an approved remote providing the runtimes:

```bash
./build_flatpak.sh --user --deps --related
```

Flatpak still needs the runtimes themselves present on the machine. If the app
will not start after an offline install, that is almost always what is missing.

### 5.5 Install, run and uninstall

Install an already-built bundle:

```bash
flatpak install dist/FancyClock.flatpak
```

Or system-wide, offline:

```bash
sudo flatpak install --system --reinstall --no-deps ./dist/FancyClock.flatpak
```

Run it:

```bash
flatpak run uk.codecrafter.FancyClock
```

Uninstall through the helper script [`cleanup_flatpak.sh`](cleanup_flatpak.sh) or
directly:

```bash
flatpak uninstall uk.codecrafter.FancyClock
```

This is the same path an end user takes, so it is the honest way to test a
release candidate.

### 5.6 Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Video skins report "moov atom not found" | The MP4s are LFS pointer files. Run `git lfs fetch --all` then `git lfs checkout`. |
| The build cannot reach PyPI | Intentional. Rebuild `vendor/` as in section 5.2. |
| The installed Flatpak will not launch | The KDE runtime is not present locally. Install it as in section 5.1. |
| Opacity control missing on Linux | Expected. The Flatpak sandbox cannot set per-window opacity, so the View menu control is hidden there. |
