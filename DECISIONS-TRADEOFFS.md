# Decisions and trade-offs

The deliberate choices Fancy Clock rests on: what was chosen, what was given
up for it and why. Each entry is the decision as the product makes it today.
The detail behind each one, with the tests that hold it, lives in
[ARCHITECTURE.md](ARCHITECTURE.md); [TECH_DEBT.md](TECH_DEBT.md) records what
only looks like debt and why it stays.

## The product as a whole

### Local first, one person, one machine

Settings and alarms are two JSON files in the per-user configuration
directory. There is no account and no server.

- **Rather than:** an account, a cloud copy or anything synchronised.
- **Gains:** nothing to sign in to; the clock and its alarms work with the
  network switched off.
- **Costs:** alarms belong to that one machine. Moving them to another means
  exporting and importing them by hand.

### Python and PySide6

The application is written in Python on Qt for Python, with Qt's own
multimedia for the video skins and the alarm sounds.

- **Rather than:** a native toolkit per platform.
- **Gains:** one code base for Windows, macOS and Linux; video playback and
  sound come with the toolkit.
- **Costs:** a large runtime for a clock; each platform needs its own
  packaging recipe.

### A clock, not a scheduler

Fancy Clock shows the time and rings alarms while it is running. It never
wakes a suspended or powered-off computer; what it missed is reported when it
next runs.

- **Rather than:** operating-system wake timers or a background service.
- **Gains:** no elevated rights; no service left running after the window
  closes; the same behaviour on every platform.
- **Costs:** an alarm set on a sleeping machine does not ring on time. The
  limit is stated in the README rather than hidden.

### Free, with nothing held back

Every copy is the whole program. There is no paid tier, no licence key and
no feature kept behind a donation; a donation link is offered instead.

- **Rather than:** a paid version or features unlocked by paying.
- **Gains:** everybody runs the same clock; nothing in it nags for money.
- **Costs:** its upkeep rests on voluntary donations and commercial licences.

## Time and the network

### NTP correction is automatic and has no switch

At startup the clock asks the public NTP pool once, trying four servers with a
short timeout each. It keeps the difference from the system clock. When none
answers it shows the system clock. There is no setting to turn this off.

- **Rather than:** trusting the system clock; an optional correction.
- **Gains:** the display is right on a machine whose clock has drifted; a clock
  that cannot reach a server still opens.
- **Costs:** one unprompted request at every launch. The correction is taken
  once per run and is not refreshed while the clock stays open.

### Two ways out and no more

The only calls that leave the machine are the NTP query and the update check.
The single-instance guard talks only to a local pipe.

- **Rather than:** fetching skins, translations or anything else at run time.
- **Gains:** a short, stated list of what the clock sends anywhere.
- **Costs:** no test counts the routes out; the list is held by review.

### Update checks: daily, anonymous, quiet unless there is news

A check runs about three seconds after launch and then once a day. It asks
GitHub for the latest published release with no identifying detail and says
nothing unless that release is newer. A version it cannot read is never
treated as newer. The check from the Help menu ignores a skipped version and
reports every outcome, including failure.

- **Rather than:** no check at all; one that reports every result.
- **Gains:** updates are found without nagging; a malformed tag cannot tell
  anybody their copy is stale; a skip is never a dead end.
- **Costs:** one unprompted request a day.

### Only published releases can prompt

The update check reads GitHub's latest-release answer, which by GitHub's own
contract leaves out drafts and pre-releases.

- **Rather than:** listing every release or tag and filtering them.
- **Gains:** a tag pushed during development can never prompt anybody.
- **Costs:** a pre-release cannot be offered to testers through the check.

### Downloads go through the browser

Choosing to download opens this platform's installer in the default browser.
Where the release has none, the release page opens instead.

- **Rather than:** downloading and installing from inside the clock.
- **Gains:** no download or install code in the application; the browser
  handles the transfer.
- **Costs:** updating takes a few more steps by hand.

## Alarms

### Alarms ring on the corrected time

An alarm fires on the same NTP-corrected clock the face shows.

- **Rather than:** the system clock, which the display does not use.
- **Gains:** an alarm rings when the clock on screen says it should.
- **Costs:** none recorded.

### One rule for daylight saving, decided in advance

A time skipped by the clocks going forward rings at the first valid minute
after the gap. A time that happens twice when the clocks go back rings once,
on the earlier occurrence. Alarm scheduling uses the standard library's
timezone data for this, because the timezone library used elsewhere cannot
tell the two occurrences apart.

- **Rather than:** one timezone library throughout; leaving the edge cases to
  whatever the library does.
- **Gains:** no alarm is silently lost in spring or rung twice in autumn.
- **Costs:** two timezone libraries in one program, each for its own job.

### One missed-alarm mechanism for sleep, quitting and crashes

The alarm file records the last moment that was checked. Every tick looks at
everything between that moment and now, so waking from sleep and starting
after a day switched off are the same code. A first launch has no such moment
and checks nothing in the past. Anything more than five minutes late is
reported as missed rather than rung.

- **Rather than:** separate handling for wake, restart and crash.
- **Gains:** one path to test; a fresh install never rings for times before it
  existed; a stale alarm does not go off long after it mattered.
- **Costs:** that moment is written at most once a minute while nothing else
  changes, so after a crash the record can be up to a minute old.

### A damaged alarm file is reported, never quietly shortened

A bad entry is skipped so the clock always starts. The number lost is shown
once at startup, in every language. An unreadable file counts as wholly
lost. A missing file is a first run, not damage.

- **Rather than:** refusing to start; skipping in silence.
- **Gains:** an alarm that will not ring is something the user is told about
  rather than discovers by oversleeping.
- **Costs:** one interruption at startup when it happens.

### Settings may fall back in silence; alarms may not

A settings file that cannot be read falls back to the defaults without a
word.

- **Rather than:** the same warning the alarm file gives.
- **Gains:** no interruption for a lost skin or opacity level.
- **Costs:** a damaged settings file resets those choices unannounced.

### Every write is all or nothing

Settings and alarms are written to a temporary file which then replaces the
real one.

- **Rather than:** writing over the file in place.
- **Gains:** a crash mid-write leaves the previous file whole.
- **Costs:** none recorded.

### Snoozing works like a phone's

Each alarm carries a default snooze length and a budget of one, three, five
or unlimited snoozes per ring. Every snooze can pick a different length; that
pick never changes the alarm's own settings. A snooze in progress survives a
restart. Editing or switching off an alarm cancels its snooze.

- **Rather than:** a fixed snooze length; snooze state kept only in memory.
- **Gains:** a snooze is not lost by restarting; a changed alarm never wakes
  somebody on its old terms.
- **Costs:** snooze state is a second kind of record to store beside the
  alarms.

### A one-off alarm switches itself off

A one-off alarm turns itself off once it has rung or been reported missed.

- **Rather than:** deleting it; leaving it on with a date in the past.
- **Gains:** it can be set again for another day without being written out
  afresh.
- **Costs:** old one-off alarms stay in the list until deleted.

### The ringing window stays until answered

A ringing alarm opens a window that stays on top of the others; closing it
counts as dismissing. A notification from the tray is sent as well where a
tray exists. The sound stops on its own after ten minutes; the window does
not.

- **Rather than:** a notification alone, which the system may hide; a sound
  that loops for ever.
- **Gains:** an alarm cannot pass unseen; an unattended machine falls quiet.
- **Costs:** the window has to be dealt with before work carries on.

### Imports add, they never merge

Importing a file adds its alarms as new ones. An import that cannot be read
is refused as a whole, unlike the clock's own file.

- **Rather than:** replacing the current alarms; matching them up by name.
- **Gains:** nothing already set is lost by an import; a bad file changes
  nothing.
- **Costs:** importing the same file twice gives every alarm twice.

### Alarm sounds made from code

The five alarm sounds are synthesised by a script from plain arithmetic, so
the same script always gives the same files.

- **Rather than:** recorded or licensed samples.
- **Gains:** no third-party audio and no licence to carry; any sound can be
  rebuilt from the source.
- **Costs:** the sounds are simple tones rather than recordings.

## Language, timezone and region

### The language follows the place

Choosing a timezone also switches the language to the one mapped to that
zone; a zone with no mapping falls back to American English. On first launch
the system's own locale is used if it reports one; the timezone map is the
fallback.

- **Rather than:** language and timezone set separately.
- **Gains:** picking a place gives its names and numerals in one step.
- **Costs:** somebody who wants another zone in their own language has to
  set the language again afterwards.

### Its own JSON locale store

Translations are JSON files, one per regional locale, read by the
application's own service. A key missing from a locale falls back to English,
then to the key itself.

- **Rather than:** Qt's own translation tools.
- **Gains:** plain data that ships unchanged by every packaging route;
  numerals in native digits where a locale defines them.
- **Costs:** the tooling for adding or repairing a key across the corpus is
  the project's own.

### Every locale carries every key; English must be accounted for

Structural tests require every key in every locale. They fail when a locale
ships the English text without an exemption naming that one language. An
exemption that is no longer English fails too, so the list can only shrink.

- **Rather than:** relying on the English fallback.
- **Gains:** a value left in English by accident cannot ship.
- **Costs:** a new key has to be translated into every language before it can
  land.

### Machine translation, checked by tests

The timezone names are translated by a maintenance tool that drives a
LibreTranslate server, by default one running on the same machine. Keys added
since arrive through scripts that carry their own table of translations.

- **Rather than:** human translators for each language; a hosted service.
- **Gains:** more than seventy languages at no cost; by default no text goes
  to a third party.
- **Costs:** machine translation leaves debris that only review or a test
  catches.

### The timezone list comes from pytz

The timezone dialog and its offset labels are drawn from pytz, as they were
before the move to the layered design.

- **Rather than:** moving the list to the standard library's zoneinfo at the
  same time.
- **Gains:** the dialog behaves exactly as it did.
- **Costs:** a second timezone library alongside the one alarms use.

## The interface

### One accent colour everywhere

Every selection uses one amber accent with near-black text, set once for the
whole application.

- **Rather than:** the platform's own highlight, which was nearly invisible
  under white text.
- **Gains:** selections can be read in every list, calendar and editor.
- **Costs:** the clock does not follow the system's highlight colour.

### Opacity has a floor; it is hidden where it cannot work

The window can be faded to a fifth of full strength and no further, from the
View menu, Ctrl with the arrow keys or Ctrl with the mouse wheel. Inside the
Flatpak sandbox, where per-window opacity cannot be set, the menu is hidden
and the keys do nothing.

- **Rather than:** a control offered everywhere; no lower limit.
- **Gains:** the window cannot be faded out of sight; no dead control on
  Linux.
- **Costs:** the Flatpak build has no opacity control.

### The tray is used where it exists

Close-to-tray is off until chosen. Where the desktop offers no tray, as on a
plain GNOME desktop, the option has no effect and closing quits rather than
hiding a window that could not be brought back.

- **Rather than:** always hiding to a tray.
- **Gains:** nothing is ever hidden beyond reach.
- **Costs:** on such desktops the window must stay open for alarms to ring.

### One copy runs

A second launch tells the first copy to come to the front, then exits.

- **Rather than:** several clocks each ringing the same alarms.
- **Gains:** every alarm rings once.
- **Costs:** none recorded.

### Retranslate what lives; look up the rest when shown

Menus and the tray, built once and kept, are retitled when the language
changes. Dialogs, notices and notifications look their text up when they are
shown. Each retitling step runs on its own, so one failing does not stop the
others.

- **Rather than:** a full retranslation pass over everything.
- **Gains:** short-lived windows need no retranslation code at all.
- **Costs:** anything new that lives for the whole run must be added to the
  retitling list.

### Skins are the video files that ship

A video skin is any MP4 file in the media folder; the menu is built from
what is there. Starfield is drawn by the program itself and needs no file;
choosing it is remembered as a choice of its own, since an empty setting means
a first run. The videos are held in Git LFS.

- **Rather than:** a list of skins written into the program; videos committed
  directly to history.
- **Gains:** a skin is added by adding a file; the repository does not grow by
  tens of megabytes each time a video is replaced.
- **Costs:** a fresh clone needs Git LFS; without it the videos arrive as
  stubs that cannot play.

## Building and installing

### PyInstaller, with its warnings treated as failures

The Windows and macOS packages are built with PyInstaller. Each of their
three build scripts reads PyInstaller's own report of what it could not
include and fails if anything that package needs is on it.

- **Rather than:** taking a finished build as a good one. PyInstaller only
  warns about a missing import and writes the executable anyway.
- **Gains:** a build made from the wrong environment fails on the build
  machine rather than in the user's hands.
- **Costs:** the list of what each package needs is kept by hand.

### Installed for one user, without administrator rights

On Windows the setup program installs into the user's own folders and
registry.

- **Rather than:** a machine-wide install.
- **Gains:** no administrator prompt.
- **Costs:** each account on a machine installs separately.

### A setup program of its own

Install, repair and removal on Windows are one bespoke program. Its payload
carries a fingerprint for every file; repair rewrites only the files whose
fingerprint no longer matches. It refuses to install or remove while the
clock is running. An upgrade moves the previous install aside and deletes it
only once the new one is in place. A failure before then puts it back; where
that cannot be done, it is kept and its folder named.

- **Rather than:** a generic installer; overwriting the old install in place.
- **Gains:** a repair that touches only what is damaged; no file is replaced
  under a running copy; a failed upgrade never leaves the user with no clock.
- **Costs:** the setup program is Fancy Clock's own to maintain; an old copy
  held open by another program can be left behind beside the new one.

### Removal takes everything

Uninstalling removes the program, its shortcuts, its start-at-sign-in entry
and the user's settings and alarms.

- **Rather than:** leaving user data behind.
- **Gains:** nothing of the clock remains on the machine.
- **Costs:** the setup program offers no way to keep the alarms; export them
  first to reinstall later.

### One sign-in entry shared by the installer and the app

The installer's checkbox and the clock's own menu toggle write the same
per-user startup entry.

- **Rather than:** an entry each.
- **Gains:** the two can never disagree; removal clears whichever made it.
- **Costs:** none recorded.

### A Flatpak that installs without reaching a remote

The Flatpak build fetches the missing Python wheels itself before it starts
and installs the result without asking Flathub for anything. An air-gapped
build can demand a cache filled beforehand. The sandbox is granted the
network for the NTP query and the update check, plus the sound server for the
alarm sounds.

- **Rather than:** a Flathub listing; filling the wheel cache by hand.
- **Gains:** a first build on a new machine works; installing touches no
  remote.
- **Costs:** the KDE runtime must already be on the machine.

### macOS releases are notarised or not built

The disk image build signs and notarises by default and stops if
notarisation fails. The Apple credential comes from the keychain unless one is
given in the environment; such a password is checked for the right shape
before the build starts. The keychain entry is named outright rather than
derived from the application's name. An unnotarised image is built only when
a local test build is asked for by name.

- **Rather than:** shipping unsigned; finding a bad password at the last step.
- **Gains:** a mistyped password costs seconds, not a full build; renaming
  the application cannot quietly change which credential is used.
- **Costs:** an Apple developer account and a Mac to build on.

### One icon master, everything derived

Every icon comes from one plain master by script. The alarm-bell badge is
composed at build time; nothing is drawn at run time.

- **Rather than:** hand-made icons per size; a badge painted by the program.
- **Gains:** every size and platform matches.
- **Costs:** changing the artwork means running the script and committing its
  output.

### LGPL, plus a commercial licence

The program is licensed under LGPL-3.0, the same licence Qt for Python
carries. A commercial licence for the author's own code is offered
separately.

- **Rather than:** one licence only.
- **Gains:** the terms sit comfortably beside the toolkit's own.
- **Costs:** two routes to explain.

### A website whose downloads never go stale

The site's download buttons point at GitHub's latest-release address with
version-free file names. A script adds the version and sizes when GitHub
answers; when it does not, the page still works. The site carries no dates.

- **Rather than:** links rewritten at every release.
- **Gains:** a release needs no site edit to be downloadable.
- **Costs:** renaming a package breaks its button until the site is changed
  to match.

## Engineering

### Layers with one place where they meet

The code is split into domain, application, infrastructure and interface,
each allowed to depend only inward, with one composition root wiring them
together. Structural tests hold every boundary.

- **Rather than:** convention alone.
- **Gains:** the rules about time, alarms and languages can be tested with no
  disk, network or screen.
- **Costs:** more modules and more explicit wiring.

### The rules never read the clock

A structural test forbids the domain layer from asking the system for the
time. Every rule is handed the moment it works on.

- **Rather than:** reading the time where it is needed.
- **Gains:** daylight-saving, missed-alarm and snooze rules can be tested at
  any moment chosen.
- **Costs:** the current time has to be passed down explicitly.

### Complete coverage where it means something

Line and branch coverage must be total over the domain, application and
infrastructure layers and over the Qt-free half of the setup program. The
interface, the setup program's Qt client, the composition root, the port
declarations and the single-instance lock are left out.

- **Rather than:** one figure over the whole program, which could only be met
  by mocking Qt.
- **Gains:** anything short of complete in the measured layers is a decision
  nobody made.
- **Costs:** interface code, including some real decisions in it, is not
  measured.

### Small modules

No module may exceed four hundred lines, across the application, the setup
program and the tests. A second test fails a module just under the cap; its
width is worked out from the cap. Delivery scripts are exempt.

- **Rather than:** letting files grow.
- **Gains:** a module is split at a real seam before the next edit forces a
  hurried one.
- **Costs:** many small files.

### No blind exception handler

The linter fails any catch-all exception handler, with no exemption for the
setup program. Handlers name what actually occurs; the few that genuinely
cannot say why beside them.

- **Rather than:** catching everything and saying nothing.
- **Gains:** a deliberate tolerance can be told from an oversight.
- **Costs:** each new handler has to justify itself.

### Tests with real parts

No mocking library. Hand-written fakes stand in for the ports; the network
time code is tested against a real local server and the stores against real
temporary files.

- **Rather than:** mocks.
- **Gains:** a passing test means the real code works.
- **Costs:** fakes are written and kept by hand.

### The version has one home

The version lives in one file. The program and its packaging read it; the
website, which cannot, is stamped from it by each Windows and macOS build.
No tracked document carries a version.

- **Rather than:** a version written wherever it is shown.
- **Gains:** a release cannot disagree with its own site.
- **Costs:** the site must be stamped before it is current.

### Two places for scripts, by question

Scripts a release runs live at the root. One-off tools for maintaining the
locale corpus live in their own folder. The test is whether deleting it would
break a release.

- **Rather than:** one scripts folder.
- **Gains:** the delivery scripts are not lost among the maintenance ones.
- **Costs:** two places to look.
