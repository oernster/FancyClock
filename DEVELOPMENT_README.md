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

`ruff` selects `BLE` on top of the defaults, so a blind `except Exception`
fails the lint. There is no per-file ignore, including for `installer/`, which
does the most privileged work in the product: exempting it would announce a
rule while excusing the code that most needs it. Catch the type that actually
occurs (`OSError` for filesystem and registry work, `RuntimeError` where a Qt
wrapper can outlive its C++ half) and reach for `# noqa: BLE001` only when the
type genuinely cannot be named, writing the fallback beside it. The three
surviving cases are documented in [`TECH_DEBT.md`](TECH_DEBT.md).

## 4. Build entry points

| Target | Command | Output |
|---|---|---|
| Windows app bundle | `python buildexe.py` | `dist-pyinstaller/FancyClock/` |
| Windows installer | `python buildinstaller.py` | `dist-installer/FancyClockSetup.exe` |
| macOS DMG (run on a Mac) | `python builddmg.py` | `fancyclock-macos-<arch>.dmg` |
| Linux Flatpak | `./build_flatpak.sh` | `dist/FancyClock.flatpak` |
| Icon assets | `python generate_icons.py` | badged `fancyclock.png` plus `assets/` from the `fancyclock_plain.png` master |
| Alarm sounds | `python generate_sounds.py` | `assets/sounds/` (deterministic stdlib synthesis) |

### Where a script lives

Two directories hold scripts. They are not two answers to one question; they
are two different kinds of thing, so both stay.

**Repo root: delivery scripts.** Anything a release runs. The table above plus
`stamp_version.py`, `compose_alarm_badge.py`, `dmg_icon.py` and `build_utils.py`.
They are invoked as part of building or stamping a release, several of them by
each other; `stamp_version.py` in particular is imported by the build
scripts from the root. They are exempt from the module size rule, since a
linear recipe of flags and steps costs more to split than it saves.

**`helper_scripts/`: one-shot corpus maintenance.** Tooling for the 243
translation files: adding a key across every locale, repairing values, auditing
for suspicious translations, driving the LibreTranslate client. Each is run by
hand when the locale corpus needs something done to it, never by a build, with
most never run twice. Keeping them out of the root is what stops the four
delivery scripts being lost among twenty maintenance ones.

The test for which a new script is: would a release break if it were deleted?
If yes it belongs at the root, otherwise in `helper_scripts/`.

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

The sandbox installs Python dependencies with
`python3 -m pip install --no-index --find-links=vendor --prefix=/app -r requirements.txt`,
so every wheel has to exist in a local `vendor/` directory before the sandbox
runs. `vendor/` is a build cache rather than source: it is gitignored, so a
fresh clone or a cleaned tree has none of them. **The build script fills it for
you**, which is why a first build on a new machine now works instead of failing
inside `flatpak-builder` with an opaque "No matching distribution".

### 5.1 Runtime prerequisites

FancyClock builds against KDE Runtime 6.8. One-time setup:

```bash
flatpak install flathub org.kde.Sdk//6.8
flatpak install flathub org.kde.Platform//6.8
```

These provide Python inside the sandbox, the Qt 6 frameworks, the ffmpeg
backend that plays the video skins and the SDK tools needed to build krb5.

### 5.2 `vendor/` and the wheel fetch

`build_flatpak.sh` works out which requirements have no matching wheel, then
downloads just those before starting the build. It asks the SDK named in the
manifest which Python version it ships and resolves wheel tags for that
interpreter rather than the host's, because the two routinely differ and a
wheel built for the host will not install in the sandbox.

Nothing needs doing by hand. To force a clean refill:

```bash
rm -rf vendor
./build_flatpak.sh --user
```

For an air-gapped build, pass `--no-fetch`. The script then never contacts PyPI
and fails with the list of missing distributions if `vendor/` is incomplete,
which is the behaviour every build had before. Populate it beforehand with:

```bash
pip download -r requirements.txt -d vendor
```

A complete `vendor/` holds the PySide6, shiboken6, pyside6-addons and
pyside6-essentials wheels plus `pytz`, `tzlocal` and `tzdata` (the IANA data
behind `zoneinfo`, which alarm scheduling depends on).

### 5.3 krb5

QtMultimedia needs `libgssapi_krb5.so.2`. The manifest at
[`uk.codecrafter.FancyClock.yml`](uk.codecrafter.FancyClock.yml) builds it as an
embedded `krb5` module, so there is nothing to install by hand.

### 5.4 Build

Before running the build, confirm the LFS assets are real files and the Flatpak
runtimes are installed. `vendor/` looks after itself unless you pass
`--no-fetch`. Then:

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
