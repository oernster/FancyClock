# FancyClock Architecture

Version: <!--VERSION-->2.0.0<!--/VERSION-->

## Invariants

Each invariant is enforced by a structural test in
[`tests/structural/test_architecture.py`](tests/structural/test_architecture.py);
the build fails when one is violated.

| Invariant | Enforced by |
|---|---|
| Domain imports only a small stdlib whitelist and other domain code | `test_domain_is_pure` |
| Domain never reads the wall clock | `test_domain_never_reads_the_wall_clock` |
| Application depends on domain and application only | `test_application_depends_on_domain_only` |
| Infrastructure never imports the UI | `test_infrastructure_never_imports_ui` |
| UI is a client of the application layer only | `test_ui_never_imports_infrastructure` |
| Only the composition root wires infrastructure | `test_composition_root_is_the_only_infrastructure_consumer` |
| No module exceeds 400 lines (build scripts exempt) | `test_no_module_exceeds_the_line_limit` |

## Dependency direction

```
UI  -->  Application  -->  Domain  <--  Infrastructure
```

- **Domain** (`fancyclock/domain/`): pure rules and values. Locale
  normalisation and the supported-locale catalog, digit translation,
  date-presentation rules, skin naming, timezone entry formatting,
  clock-offset arithmetic and the alarm model (`alarms.py`: the frozen
  `Alarm`, `SnoozeState` and `AlarmsState` value objects with the colour,
  sound and snooze presets; `alarm_schedule.py`: pure occurrence math with
  the DST policy, tick-window evaluation with the missed-alarm grace and
  the next-alarm summary). Stdlib only; no I/O, no Qt, no wall clock.
- **Application** (`fancyclock/application/`): services and ports.
  `LocalizationService`, `TimeService`, `SettingsService`, `SkinService`,
  `TimezoneService`, `AlarmService` (CRUD, tick evaluation and its
  consequences, snooze episodes with budgets, import/export, the
  NTP-corrected now) and the `ResourcePaths` value object. Ports are
  `typing.Protocol` interfaces in `ports.py` (including `AlarmStore`,
  `AlarmPorter` and `AutostartManager`); services receive their
  dependencies by constructor injection.
- **Infrastructure** (`fancyclock/infrastructure/`): implementations of the
  ports. NTP over UDP with a system-clock fallback, the JSON settings store,
  the JSON alarm store and porter (tolerant load, strict import), the
  per-OS autostart adapters (HKCU Run key, macOS LaunchAgent, XDG
  autostart, null under Flatpak), the per-locale translation repository,
  the timezone-to-locale map, the system locale probe, the pytz timezone
  catalog (fold-aware tzinfo via zoneinfo for alarm scheduling), the media
  library, the resource path resolver and the Qt single-instance guard.
- **UI** (`fancyclock/ui/`): PySide6 widgets. The clock window and its
  behaviour mixins, the analog and digital clock widgets, the galaxy effect,
  the dialogs and the alarm suite (`ui/alarms/`: controller, tray icon,
  manager and editor dialogs, the clock-face time picker, the persistent
  firing window, the missed-alarms summary, toasts and the sound player).
  The UI talks only to application services; resource locations arrive as
  a `ResourcePaths` value built by the composition root.
- **Composition root** (`fancyclock/main.py`): the only module that imports
  infrastructure. It builds every implementation, injects it into the
  services and hands those to `ClockWindow`. The repo-root `main.py` is a
  thin wrapper.

`fancyclock/version.py` sits outside the layers: it reads the canonical
VERSION file (repo root in dev, the bundle root when frozen) and carries the
app identity constants shared with the Windows installer.

## Execution flow

1. `main.py` calls `fancyclock.main.main()`.
2. Qt logging filters, the Windows AppUserModelID and the desktop file name
   are applied, then `QApplication` starts.
3. The single-instance guard either becomes primary or pings the existing
   instance and exits.
4. The composition root builds infrastructure, services and the window.
5. `ClockWindow` synchronises the clock offset (best effort), restores the
   saved locale, timezone and skin, then starts a 1 s tick timer and a
   16 ms animation timer.
6. Each tick computes UTC plus the NTP offset, converts to the selected
   timezone and pushes the result to both clock widgets via `tick()`; the
   same tick drives `AlarmService.tick()`, which evaluates the window since
   the previous tick and surfaces ringing and missed alarms through the
   alarms UI controller.

## Design decisions

| Decision | Rationale |
|---|---|
| Locale data stays in `localization/translations/` at the repo root | 243 JSON files are data, not code; every packaging path (PyInstaller add-data, Flatpak cp, dev tree) ships the directory unchanged |
| Duck-typed dates in `LocalizationService` | The UI passes `QDate`; the application layer must not import Qt, so weekday/day/month are read structurally |
| The first non-empty locale probe candidate wins | Mirrors the original detection behaviour; the timezone map is a fallback for systems that report no locale at all |
| Unmapped timezones fall back to `en_US` | Preserves the original behaviour when a timezone has no locale mapping |
| pytz (not zoneinfo) for the timezone catalog | The timezone dialog and the offset labels match the shipped behaviour; migration is possible but out of scope for the refactor |
| `SettingsService` mirrors Qt's AppConfigLocation layout | The installer's uninstall can remove the same per-user tree via platformdirs |
| Coverage omits `ui/*`, `main.py`, `ports.py` and the single-instance guard | UI and Qt IPC are deliberately untested (no Qt mocking); Protocol bodies and the composition root have no behaviour of their own |
| Alarm scheduling uses zoneinfo fold semantics, not pytz | The DST policy (nonexistent wall times step to the first valid instant; ambiguous times fire once, on the earlier instant) needs PEP 495 folds, which pytz ignores; the catalog resolves the same IANA ids through zoneinfo for alarms only |
| Alarms fire on the NTP-corrected clock | The firing instant must match what the on-screen clocks show, so `AlarmService.now_utc()` applies the same offset the display uses |
| One missed-alarm mechanism covers sleep, quit and crash | The store persists a `last_evaluated_utc` watermark (throttled to one write a minute); every tick evaluates `(watermark, now]`, so wake-from-suspend and machine-off-between-runs are the same code path |
| Snooze state is separate from alarm config and survives restarts | `SnoozeState` (episode budget, last-used duration, wakeup instant) persists beside the frozen `Alarm`; ad-hoc snooze picks never mutate configured defaults and reset when the episode ends |
| A first launch evaluates an empty window | A fresh store has no watermark, so historical occurrences can never fire on install |
| The tray degrades to a plain window | `QSystemTrayIcon.isSystemTrayAvailable()` is false on some Linux desktops (vanilla GNOME); close-to-tray disables rather than hiding an unrecoverable window |
| The installer and the app share one Run value | Both write `HKCU\...\Run\FancyClock`, so the sign-in checkbox and the Alarms menu toggle can never disagree |

## Quality enforcement

- `pytest` runs unit, integration and structural tests with a hard
  `--cov-fail-under=100` gate (see `.coveragerc` for the measured surface).
- No mock libraries: hand-written fakes implement the ports; infrastructure
  tests use real temp files and a real local UDP server.
- `black --check`, `flake8` and `ruff check` are standing steps.
- The version is never hardcoded outside the VERSION file; static docs are
  stamped by `stamp_version.py`, which the build scripts invoke.

## Delivery

| Platform | Entry point | Output |
|---|---|---|
| Windows | `buildexe.py` then `buildinstaller.py` | `dist-installer/FancyClockSetup.exe` |
| macOS | `builddmg.py` | `fancyclock-macos-<arch>.dmg` |
| Linux | `build_flatpak.sh` | `dist/FancyClock.flatpak` |

All icon assets derive from the 1024px master `fancyclock.png` via
`generate_icons.py` into `assets/`.
