# FancyClock Architecture

Version: <!--VERSION-->1.6.0<!--/VERSION-->

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
  date-presentation rules, skin naming, timezone entry formatting and
  clock-offset arithmetic. Stdlib only; no I/O, no Qt, no wall clock.
- **Application** (`fancyclock/application/`): services and ports.
  `LocalizationService`, `TimeService`, `SettingsService`, `SkinService`,
  `TimezoneService` and the `ResourcePaths` value object. Ports are
  `typing.Protocol` interfaces in `ports.py`; services receive their
  dependencies by constructor injection.
- **Infrastructure** (`fancyclock/infrastructure/`): implementations of the
  ports. NTP over UDP with a system-clock fallback, the JSON settings store,
  the per-locale translation repository, the timezone-to-locale map, the
  system locale probe, the pytz timezone catalog, the media library, the
  resource path resolver and the Qt single-instance guard.
- **UI** (`fancyclock/ui/`): PySide6 widgets. The clock window and its
  behaviour mixins, the analog and digital clock widgets, the galaxy effect
  and the dialogs. The UI talks only to application services; resource
  locations arrive as a `ResourcePaths` value built by the composition root.
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
   timezone and pushes the result to both clock widgets via `tick()`.

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
