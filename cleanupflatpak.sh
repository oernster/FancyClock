#!/usr/bin/env bash
set -euo pipefail

# Uninstall FancyClock Flatpak (system-wide).
# App-id comes from [`uk.codecrafter.FancyClock.yml`](uk.codecrafter.FancyClock.yml:1).
APP_ID="uk.codecrafter.FancyClock"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "flatpak is not installed or not on PATH" >&2
  exit 127
fi

echo "Uninstalling system-wide Flatpak app: ${APP_ID}"
sudo flatpak uninstall --system -y "${APP_ID}" || true

echo "Done. Remaining installs (if any):"
flatpak list | grep -i fancyclock || true

