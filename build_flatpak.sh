#!/usr/bin/env bash
set -euo pipefail

MANIFEST="uk.codecrafter.FancyClock.yml"
APP_ID="uk.codecrafter.FancyClock"
BUILDDIR="build-flatpak"
DISTDIR="dist"
REPO_DIR="${DISTDIR}/repo"
BUNDLE_PATH="${DISTDIR}/FancyClock.flatpak"

INSTALL_SCOPE="user" # user|system

if [[ "${1:-}" == "--system" ]]; then
  INSTALL_SCOPE="system"
  shift
elif [[ "${1:-}" == "--user" ]]; then
  INSTALL_SCOPE="user"
  shift
elif [[ -t 0 ]]; then
  echo "Install scope?"
  echo "  1) User (no sudo)"
  echo "  2) System-wide (sudo)"
  read -r -p "Choose [1/2] (default 1): " _choice
  if [[ "${_choice}" == "2" ]]; then
    INSTALL_SCOPE="system"
  fi
fi

echo "Building ${APP_ID} from ${MANIFEST} (install scope: ${INSTALL_SCOPE})..."

mkdir -p "${DISTDIR}"

if [[ "${INSTALL_SCOPE}" == "user" ]]; then
  flatpak-builder \
    --user \
    --force-clean \
    --install \
    --repo="${REPO_DIR}" \
    "${BUILDDIR}" \
    "${MANIFEST}"
else
  # Build as the current user (no sudo), then install the resulting bundle system-wide.
  # This avoids root-owned build artifacts in the working tree.
  flatpak-builder \
    --force-clean \
    --repo="${REPO_DIR}" \
    "${BUILDDIR}" \
    "${MANIFEST}"
fi

echo
echo "Bundling to ${BUNDLE_PATH}..."

flatpak build-bundle \
  "${REPO_DIR}" \
  "${BUNDLE_PATH}" \
  "${APP_ID}"

if [[ "${INSTALL_SCOPE}" == "system" ]]; then
  echo
  echo "Installing system-wide from bundle (requires sudo)..."
  sudo flatpak install --system --reinstall -y "${BUNDLE_PATH}"
fi

echo
echo "Done."
echo
echo "Bundle created at:"
echo "  ${BUNDLE_PATH}"
echo
echo "Run installed build with:"
echo "  flatpak run ${APP_ID}"
