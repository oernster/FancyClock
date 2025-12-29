# Development Notes

## Flatpak (local/offline)

This repo includes a Flatpak manifest at [`uk.codecrafter.FancyClock.yml`](uk.codecrafter.FancyClock.yml:1) and a build script at [`build_flatpak.sh`](build_flatpak.sh:1).

### Build and install

Build and install per-user (no sudo):

```bash
./build_flatpak.sh --user
```

System-wide install: supported by [`build_flatpak.sh`](build_flatpak.sh:1). When you choose the system option, it will print the exact `sudo flatpak install --system ...` command, and (optionally) ask whether to run it.

**No Flathub / offline policy:** [`build_flatpak.sh`](build_flatpak.sh:1) defaults to an offline-safe install by using `flatpak install --bundle --no-deps --no-related`. This prevents Flatpak from trying to use `flathub` (or any other remote) during the install step.

If you explicitly want to disable those offline-safe flags (only if you have an approved remote that provides runtimes/related refs):

```bash
./build_flatpak.sh --user --deps --related
```

If the app fails to run afterwards, it means the required runtime(s) are not installed locally yet.

If you run [`build_flatpak.sh`](build_flatpak.sh:1) without flags in an interactive terminal, it will prompt for the install scope.

Build outputs:

- Flatpak bundle: [`dist/FancyClock.flatpak`](dist/FancyClock.flatpak:1)
- Local OSTree repo: [`dist/repo`](dist/repo:1)

### Run

```bash
flatpak run uk.codecrafter.FancyClock
```

### Install the bundle manually (offline)

If you already built the bundle at [`dist/FancyClock.flatpak`](dist/FancyClock.flatpak:1):

```bash
sudo flatpak install --system --reinstall --no-deps ./dist/FancyClock.flatpak
flatpak run uk.codecrafter.FancyClock
```

### Offline/runtime note

Flatpak still requires the relevant runtime(s) to be installed on the machine. If you do not use network remotes, the runtime(s) must already be present locally (or be provided via your own local repo/media).

### Uninstall

Use the uninstall helper script [`cleanupflatpak.sh`](cleanupflatpak.sh:1):

```bash
./cleanupflatpak.sh
```
