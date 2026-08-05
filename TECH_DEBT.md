# FancyClock: Technical Debt

A standing reference to the project's outstanding technical debt. It records what is still open, weighs whether each item is worth doing and gives the rationale. Every item is a behaviour-preserving internal concern: nothing here proposes reverting a feature or changing any UI or UX behaviour. Scope is the whole repository (the `fancyclock` package, the bespoke installer, the delivery scripts, the bundled media and the 243 translation files) read against `ARCHITECTURE.md` and `tests/structural/test_architecture.py`.

This is a well-kept repository, so this file is short. `VERSION` and `stamp_version.py` are correct, the media are in Git LFS, the structural suite covers domain purity, wall-clock access, all four layer directions and the composition root. Only four files in the whole tree exceed 350 lines, one of them an exempt build script. The items below are what is left.

---

## 1. `installer/ui/_main_window_actions.py` is over the cap and outside the test that would say so

At 406 lines it exceeds the 400-line limit. `tests/structural/test_architecture.py` scopes itself to `PACKAGE_DIR` and `TESTS_DIR`, so `installer/` is never measured and nothing reports it.

Six lines over is not an emergency; taking it to 350 by extracting one cohesive concern is a small piece of work. The more useful half is extending the structural test over `installer/` at the same time, so the installer is held to the same rule as everything else rather than being the one directory that quietly is not.

`installer/ops/install_ops.py` at 357 is fine and would pass the moment the scope widens.

## 2. Forty-two broad exception handlers, none with a stated reason

`except Exception` (or bare `except`) across `fancyclock/`, with none of them saying why. They cluster and each cluster deserves a different answer:

- **`infrastructure/json_alarm_store.py` (five handlers).** These are deliberate and the docstring says so: "tolerant of missing or bad data". The design consequence is worth writing down, because it is not obvious. A single malformed entry in the alarms file is silently skipped by the `continue` in the loop, so a user whose alarm file is partially corrupt loses that alarm with no message and no log line. For an alarm clock, silently not ringing is the worst failure mode available. The tolerance is right; the silence is not. Count what was dropped and surface it once.
- **`infrastructure/` generally (six more).** `ntp_time_source`, `system_locale_probe`, `timezone_locale_map` and `translations_repo` plus `json_settings_store`: network, OS locale and file reads that should degrade to a default rather than crash a clock. Correct behaviour; each wants one line saying what it falls back to.
- **`ui/` (twenty-seven).** Sixteen of those are in `window_locale.py` alone, with the rest spread across `analog_clock.py`, `window.py`, `window_drag.py`, `window_opacity.py` and `dialogs.py`. Qt paint and window-manager calls where an exception is worse than a missing visual effect, so the lowest value to change: give them the house `# noqa: BLE001` plus a reason and move on. The concentration in `window_locale.py` is the part worth a second look, because a retranslation pass that swallows sixteen different failures can leave the UI half-translated with nothing said.
- **`application/` (three) and `main.py` (one).** The application layer is meant to be the reasoned part of the codebase, so a broad catch in `alarms.py` or `localization.py` is the least defensible of the four clusters. Narrow these to the exception actually expected.

None of this changes behaviour. It makes each decision reviewable, which is the point.

## 3. The UI layer is omitted from the gate in full

`.coveragerc` omits `fancyclock/ui/*` along with `main.py`, `application/ports.py` and `infrastructure/single_instance.py`. The last three are composition root, Protocol declarations and a platform lock; all three are correct omissions.

The UI omission is the standard portfolio position and is correct for painting and layout. It is recorded here only so the omission is never read as "the UI has no logic": `window_locale.py`, `window_drag.py` and the alarm-badge composition carry real decisions. As those grow, they want pushing down into `fancyclock/application`, where the gate can see them.

## 4. Four generator scripts at root with no single convention

`generate_icons.py`, `generate_sounds.py`, `compose_alarm_badge.py` and `stamp_version.py` sit at root beside `helper_scripts/`. All four are legitimate build-time generators and all four are correctly exempt from the module cap.

The debt is only that `helper_scripts/` exists as well, so there are two answers to "where do build helpers live". Pick one and move the odd ones out. Trivial, listed for completeness.

---

## Looks like debt, not worth touching

- `tests/application/test_alarm_service.py` at 382 lines. Inside the danger band, so it wants taking to 350 when next touched. It is under the cap and the structural test covers `TESTS_DIR`, so the rule will catch it if it grows.
- The 243 translation JSON files under `localization/translations/`. That is the i18n store and it is the intended design.
- `localization/` sitting outside the `fancyclock` package. It is data bundled by the delivery scripts rather than importable code; the resource resolver already handles the dev, Nuitka, PyInstaller and Flatpak cases.
- `timezone_locale_map.json` at root rather than under `localization/`. One file, referenced by one module, tested by `test_timezone_locale_map.py`.
- `FancyClock.spec` and `FancyClockSetup.spec` at root are PyInstaller artefacts and are untracked.
- The twenty-one tracked PNGs plus the `.ico` and `.icns`. Emitted by `generate_icons.py` from a single master and consumed by named packaging paths.

## Not debt (do not "fix" these)

These look like candidates but are correct as they stand; changing them would regress or add cost for nothing.

- **`tests/structural/test_architecture.py`.** Domain purity, a wall-clock ban in the domain, all four layer directions and a composition-root whitelist. For a clock application, `test_domain_never_reads_the_wall_clock()` is exactly the right invariant and it is easy to imagine it being weakened for convenience. Do not.
- **`VERSION` with `stamp_version.py` writing the delimited tokens** into `docs/` only, called from the build scripts. Correctly implemented single source of truth. The delivery side of this repository is in good order.
- **The `media/*.mp4` skins in Git LFS.** The working tree is identical to a plain checkout and history no longer grows by tens of megabytes each time a backdrop is replaced. The one cost is that a fresh machine needs `git lfs install` before the videos are real files; that is documented in the README and the development guide.
- **The JSON locale system and the custom localisation manager** rather than Qt Linguist. This is the portfolio's deliberate i18n approach and FancyClock is one of its two reference implementations.
- **`uk.codecrafter.FancyClock.yml` and `.metainfo.xml` tracked at root** while other projects generate their Flatpak manifest inside the build script. Both approaches work; a committed manifest is easier to review and this one is complete.
- **`infrastructure/single_instance.py` omitted from coverage.** A per-user OS lock. Testing it would test the platform.
- **The alarm badge being composed at build time** (`compose_alarm_badge.py`) rather than drawn at runtime. Deliberate: the icon rule in this portfolio is one master, everything derived, nothing painted at runtime.
