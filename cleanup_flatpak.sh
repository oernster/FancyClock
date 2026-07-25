#!/usr/bin/env bash
set -euo pipefail

# Uninstall FancyClock Flatpak from whichever scope(s) it's installed in.
# App-id comes from [`uk.codecrafter.FancyClock.yml`](uk.codecrafter.FancyClock.yml:1).
# build_flatpak.sh installs per-user by default, so a system-only uninstall
# leaves the app in place. Handle both --user and --system here.
APP_ID="uk.codecrafter.FancyClock"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "flatpak is not installed or not on PATH" >&2
  exit 127
fi

# Remove from the user scope (no sudo needed).
if flatpak list --user --columns=application 2>/dev/null | grep -qx "${APP_ID}"; then
  echo "Uninstalling user Flatpak app: ${APP_ID}"
  flatpak uninstall --user -y "${APP_ID}" || true
else
  echo "Not installed in user scope: ${APP_ID}"
fi

# Remove from the system scope (needs sudo).
if flatpak list --system --columns=application 2>/dev/null | grep -qx "${APP_ID}"; then
  echo "Uninstalling system-wide Flatpak app: ${APP_ID}"
  sudo flatpak uninstall --system -y "${APP_ID}" || true
else
  echo "Not installed in system scope: ${APP_ID}"
fi

echo "Done. Remaining installs (if any):"
flatpak list | grep -i fancyclock || echo "  (none)"
