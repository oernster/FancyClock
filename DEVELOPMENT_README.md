# Development Notes

## Flatpak (local/offline)

This repo includes a Flatpak manifest at [`uk.codecrafter.FancyClock.yml`](uk.codecrafter.FancyClock.yml:1) and a build script at [`build_flatpak.sh`](build_flatpak.sh:1).

### Build and install

Build and install per-user (no sudo):

```bash
./build_flatpak.sh --user
```

Build and install system-wide (sudo install step; build artifacts remain user-owned):

```bash
./build_flatpak.sh --system
```

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
sudo flatpak install --system --reinstall ./dist/FancyClock.flatpak
flatpak run uk.codecrafter.FancyClock
```

### Offline/runtime note

Flatpak still requires the relevant runtime(s) to be installed on the machine. If you do not use network remotes, the runtime(s) must already be present locally (or be provided via your own local repo/media).

### Uninstall

Use the uninstall helper script [`cleanupflatpak.sh`](cleanupflatpak.sh:1):

```bash
./cleanupflatpak.sh
```

