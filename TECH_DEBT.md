# FancyClock: Technical Debt

A standing reference to the project's outstanding technical debt. It records what is still open, weighs whether each item is worth doing and gives the rationale. Every item is a behaviour-preserving internal concern: nothing here proposes reverting a feature or changing any UI or UX behaviour. Scope is the whole repository (the `fancyclock` package, the bespoke installer, the delivery scripts, the bundled media and the 243 translation files) read against `ARCHITECTURE.md` and `tests/structural/test_architecture.py`.

This is a well-kept repository, so this file is short. `VERSION` and `stamp_version.py` are correct, the media are in Git LFS, the structural suite covers domain purity, wall-clock access, all four layer directions, the composition root and the module size rule across the application package, the setup program and the tests. Two files in the whole tree exceed 350 lines: `installer/ops/install_ops.py` at 357, which is measured and under the cap, plus `builddmg.py` at 360, which is an exempt delivery script. The items below are what is left.

---

## 1. Nothing enforces the broad-handler convention outside the app package

`fancyclock/` now carries no unexplained `except Exception`: each one is either
narrowed to the exceptions actually expected or marked `# noqa: BLE001` with the
fallback it takes written beside it. Nothing stops the next one being added
without a reason.

The fix is a `[tool.ruff]` block selecting `BLE` on top of the default rules, so
an unexplained broad catch fails the lint rather than relying on review. That
cannot be switched on yet: `installer/` carries 48 of them and `helper_scripts/`
8. Turning the rule on with a per-file ignore for the installer would
announce a rule while exempting the code that does the most privileged work in
the product. The installer is the piece worth doing first, since a swallowed
exception there is a half-installed application with nothing said.

## 2. The UI layer is omitted from the gate in full

`.coveragerc` omits `fancyclock/ui/*` along with `main.py`, `application/ports.py` and `infrastructure/single_instance.py`. The last three are composition root, Protocol declarations and a platform lock; all three are correct omissions.

The UI omission is the standard portfolio position and is correct for painting and layout. It is recorded here only so the omission is never read as "the UI has no logic": `window_locale.py`, `window_drag.py` and the alarm-badge composition carry real decisions. As those grow, they want pushing down into `fancyclock/application`, where the gate can see them.

---

## Looks like debt, not worth touching

- The 243 translation JSON files under `localization/translations/`. That is the i18n store and it is the intended design.
- `localization/` sitting outside the `fancyclock` package. It is data bundled by the delivery scripts rather than importable code; the resource resolver already handles the dev, Nuitka, PyInstaller and Flatpak cases.
- `timezone_locale_map.json` at root rather than under `localization/`. One file, referenced by one module, tested by `test_timezone_locale_map.py`.
- `FancyClock.spec` and `FancyClockSetup.spec` at root are PyInstaller artefacts and are untracked.
- The twenty-one tracked PNGs plus the `.ico` and `.icns`. Emitted by `generate_icons.py` from a single master and consumed by named packaging paths.

## Not debt (do not "fix" these)

These look like candidates but are correct as they stand; changing them would regress or add cost for nothing.

- **`tests/structural/test_architecture.py`.** Domain purity, a wall-clock ban in the domain, all four layer directions, a composition-root whitelist and the module size rule in two tiers: the 400-line cap, plus a danger band whose width is derived from the cap so the two numbers cannot drift apart. For a clock application, `test_domain_never_reads_the_wall_clock()` is exactly the right invariant and it is easy to imagine it being weakened for convenience. Do not.
- **`VERSION` with `stamp_version.py` writing the delimited tokens** into `docs/` only, called from the build scripts. Correctly implemented single source of truth. The delivery side of this repository is in good order.
- **The `media/*.mp4` skins in Git LFS.** The working tree is identical to a plain checkout and history no longer grows by tens of megabytes each time a backdrop is replaced. The one cost is that a fresh machine needs `git lfs install` before the videos are real files; that is documented in the README and the development guide.
- **Two script directories: the repo root and `helper_scripts/`.** This was recorded as debt on the grounds that there were two answers to "where do build helpers live". There are not: there are two questions. The root holds delivery scripts, the ones a release runs and which import each other (`stamp_version.py` is imported by the build scripts from there). `helper_scripts/` holds one-shot maintenance tooling for the 243-file locale corpus, run by hand and mostly never run twice. Merging them either buries four delivery scripts among twenty maintenance ones or moves `stamp_version.py` away from the scripts that import it. The distinction is written down in `DEVELOPMENT_README.md` with the test for which a new script is.
- **The JSON locale system and the custom localisation manager** rather than Qt Linguist. This is the portfolio's deliberate i18n approach and FancyClock is one of its two reference implementations.
- **`ENGLISH_BY_DESIGN` and `ACCEPTED_ENGLISH` in `tests/structural/test_translation_coverage.py`.** These are not an untranslated backlog. The first names keys whose English value is correct in any language (proper nouns, `OK`, the digit table, plus the month and day abbreviations that coincide across most European languages by design, so equality there proves nothing either way). The second names the specific locales that legitimately write a word exactly as English: French `Licence`, German `Version`, Dutch `Website`, Nordic `Alarm` and `Spiral`, Indonesian `Edit`. Every entry is a claim about one language, which is why they are listed individually rather than waved through by key. The list may only shrink: `test_accepted_english_is_still_english` fails when an entry has since been translated, so an exemption cannot outlive the value it excused.
- **`uk.codecrafter.FancyClock.yml` and `.metainfo.xml` tracked at root** while other projects generate their Flatpak manifest inside the build script. Both approaches work; a committed manifest is easier to review and this one is complete.
- **`infrastructure/single_instance.py` omitted from coverage.** A per-user OS lock. Testing it would test the platform.
- **The alarm badge being composed at build time** (`compose_alarm_badge.py`) rather than drawn at runtime. Deliberate: the icon rule in this portfolio is one master, everything derived, nothing painted at runtime.
