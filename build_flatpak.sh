#!/usr/bin/env bash
set -euo pipefail

MANIFEST="uk.codecrafter.FancyClock.yml"
APP_ID="uk.codecrafter.FancyClock"
BUILDDIR="build-flatpak"
DISTDIR="dist"
REPO_DIR="${DISTDIR}/repo"
BUNDLE_PATH="${DISTDIR}/FancyClock.flatpak"

echo "Building and installing ${APP_ID} from ${MANIFEST}..."

mkdir -p "${DISTDIR}"

flatpak-builder \
  --user \
  --force-clean \
  --install \
  --repo="${REPO_DIR}" \
  "${BUILDDIR}" \
  "${MANIFEST}"

echo
echo "Bundling to ${BUNDLE_PATH}..."

flatpak build-bundle \
  "${REPO_DIR}" \
  "${BUNDLE_PATH}" \
  "${APP_ID}"

echo
echo "Done."
echo
echo "Bundle created at:"
echo "  ${BUNDLE_PATH}"
echo
echo "Run installed build with:"
echo "  flatpak run ${APP_ID}"
