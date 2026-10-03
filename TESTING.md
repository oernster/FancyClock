# Testing

How Fancy Clock is tested: running the checks, reading what they say, what the
gate holds and what it leaves out, the rules a run by hand has to follow and
how a new test or guard is written. The layer rules themselves are in
[ARCHITECTURE.md](ARCHITECTURE.md); setting up the environment the tests run in
is in [DEVELOPMENT.md](DEVELOPMENT.md).

## Running the checks

From the repository root, with the venv active:

```
python -m pytest
python -m black --check .
python -m flake8 .
python -m ruff check .
```

`pytest` alone is the gated run: the options in `pyproject.toml` add the
coverage measurement and the floor, so nothing else needs passing to it. Add
`-v` to see each test named as it runs.

**black, flake8 and ruff are not part of the suite.** No test runs them, so a
formatting or lint regression passes `pytest` untouched. Run all four and read
the exit code of each.

**A full run takes a few seconds.** Measured on 2026-10-03: 392 tests on
Windows, all passing, in about 8 seconds.

**Read the exit code, never the text.** The run prints the coverage table then
one summary line. A search of the output for a result word is still not safe,
since coverage rows are named after modules. `0` means the tests passed AND the
floor was met; anything else means read the failures above the table. For a
count of tests without running them, run `python -m pytest --co --no-cov`: it
lists one test ID per line and ends with a `N tests collected` total. Adding
`-q` there gives no total; `addopts` already holds one `-q`, so the second
makes it quieter still and it prints only a count per test file.

## What the gate holds

The floor is 100% coverage of lines AND branches over the `fancyclock` package
and the Qt-free half of the setup program (`--cov=fancyclock --cov=installer
--cov-branch --cov-fail-under=100` in `pyproject.toml`; `branch = True` in
`.coveragerc`). A line that ran is not enough: both arms of every decision must
run too. Nothing inside the measured surface carries a `# pragma: no cover`;
the only four in the tree guard `TYPE_CHECKING` imports in `installer/ui`
modules that are omitted anyway.

Inside the floor from `installer/`: the install, upgrade, reinstall, repair and
uninstall operations, the payload and manifest access, the uninstall registry
entry and the Run value, shortcut paths and removal, process detection, version
comparison, the operation rules, the CLI, logging setup and the payload
builder. The three `installer/ui` modules that never import PySide6 (`themes`,
`_main_window_types` and `lgpl3_license_text`) are inside it too.

Outside the floor, stated in full so the number is not read as more than it is:

| Omitted | Why |
|---|---|
| `fancyclock/main.py` | the composition root |
| `fancyclock/ui/*` | the Qt client; one suite drives the real window (below) but it is not measured |
| `fancyclock/application/ports.py` | Protocol definitions with nothing to execute |
| `fancyclock/infrastructure/single_instance.py` | the single-instance lock |
| `installer/app.py` and the ten `installer/ui` modules that import PySide6, each named in `.coveragerc` | the setup program's Qt client, on the same grounds as `fancyclock/ui` |
| `create_shortcut` in `installer/ops/shortcuts.py`, excluded by name in `.coveragerc` | it writes a `.lnk` through the Shell Link COM API, so it can only act on the real machine; tests replace it with a recorder |
| the root build scripts and `helper_scripts/` | build and corpus maintenance tooling |

## Running it by hand

- **No window, provided the platform is unset.** `tests/ui/conftest.py` sets
  `QT_QPA_PLATFORM` to `offscreen` with `setdefault`, so it applies only when
  the variable is not already set. A shell that already has it set to something
  else puts the window on screen.
- **Your settings and alarms are never written.** Every test that writes builds
  its store over pytest's `tmp_path`. One test constructs a store at the real
  default folder, only to check the path it resolves; it writes nothing. This
  holds by convention: no fixture redirects the real folder and no guard checks
  it, so a new test has to keep to it.
- **The setup program's tests never touch the real machine.** An autouse
  fixture in `tests/installer/conftest.py` redirects `USERPROFILE`,
  `LOCALAPPDATA` and `APPDATA` into `tmp_path`, swaps `winreg` for an in-memory
  hive and replaces the COM shortcut writer, process detection, the detached
  PowerShell delete helper and the retry sleep with recorders. No test in that
  folder writes the registry, the Start Menu, the Desktop or the real profile.
  None starts a process.
- **Nothing leaves the machine.** The NTP source is tested against a real UDP
  server on the loopback address; the release source is handed a stand-in
  opener, with `urlopen` patched where the default opener is checked; the
  window suite replaces the reference time source so it never reaches an NTP
  server.

## Where the tests live

`tests/` mirrors the package, one directory a layer, plus one for the setup
program:

| Directory | What it tests | Against |
|---|---|---|
| `domain/` | alarms, schedules, dates, digits, locales, skins, time sync, timezones, pure | values built in the test |
| `application/` | the services and the update check | hand-written fakes of every port (`tests/application/alarm_fakes.py` holds the alarm ones) |
| `infrastructure/` | the JSON stores, the clock, the NTP source, the release source, the catalogues and the translations | real files in a temporary folder, the shipped data files, a loopback UDP server, a stand-in HTTP opener |
| `installer/` | the setup program's operations, state and supporting modules | real files and folders in `tmp_path`, with hand-written fakes at the operating-system seams (`tests/installer/installer_fakes.py`) |
| `ui/` | the chosen skin surviving a restart | the real `ClockWindow` over a real `QApplication`, offscreen |
| `structural/` | the rules no single test can see | the source tree and the shipped locale files |
| `tests/` root | the package export and the version module | the package itself |

## Writing a test

- **No mocking library.** A port is stood in for by a hand-written fake class
  (`FakeClock`, `FakeStore`, `FakeTimeSource`, `FakeReleaseSource` and the
  rest), defined in the test that needs it or in a `*_fakes.py` beside it.
  Environment and attributes are redirected with pytest's own `monkeypatch`.
- **Anything that writes takes `tmp_path`.** Build the store over it, as every
  existing test does; see "Your settings and alarms are never written" above.
- **The window.** `tests/ui/conftest.py` provides one session-wide `qapp` and
  closes every top-level widget a test leaves behind.
  `tests/ui/test_window_skin_persistence.py` builds the real window over a real
  settings file in a temporary folder; start from it rather than writing
  another.

## Guards

A structural test checks the source tree rather than behaviour, so a rule holds
for code nobody has written yet. The architecture checks read the source with
`ast` and never import it, so they run without Qt.

| Guard | Holds |
|---|---|
| `test_architecture.py` | domain purity, no wall-clock read in the domain, the layer directions, the composition root as the only consumer of infrastructure, the 400 line cap and the danger band below it |
| `test_translation_coverage.py` | every locale carries every reference key and none silently ships the English value |

**A guard is not trusted until it has been seen to fail.** A new guard is
proved by planting the violation it exists to catch and reading the failure,
then restoring the tree in a `finally` block so an interrupted proof cannot
leave the plant behind. A test written for a defect is run before the fix,
where it has to fail for the reason named, not merely fail.

---

See also [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md) and
[DEVELOPMENT.md](DEVELOPMENT.md).
