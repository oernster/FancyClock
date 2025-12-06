#!/usr/bin/env bash
set -euo pipefail

MANIFEST="uk.codecrafter.FancyClock.yml"
APP_ID="uk.codecrafter.FancyClock"
BUILDDIR="build-flatpak"

echo "Building and installing ${APP_ID} from ${MANIFEST}..."

flatpak-builder \
  --user \
  --force-clean \
  --install \
  "${BUILDDIR}" \
  "${MANIFEST}"

echo
echo "Done. Run with:"
echo "  flatpak run ${APP_ID}"
