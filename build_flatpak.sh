#!/usr/bin/env bash
set -euo pipefail

MANIFEST="uk.codecrafter.FancyClock.yml"
APP_ID="uk.codecrafter.FancyClock"
BUILDDIR="build-flatpak"
DISTDIR="dist"
REPO_DIR="${DISTDIR}/repo"
# Emit the final bundle in the repo base directory for easy access.
BUNDLE_PATH="FancyClock.flatpak"

ORIG_ARGC=$#

INSTALL_SCOPE="user" # user|system

# Install behavior defaults (offline / no-remotes):
# - `--bundle` ensures we're installing the local .flatpak bundle.
# - `--no-deps` prevents runtime dependency resolution (avoids touching remotes).
# - `--no-related` prevents installing related refs (e.g. locales/debug) that can
#   also trigger remote lookups.
INSTALL_NO_DEPS=1
INSTALL_NO_RELATED=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --system)
      INSTALL_SCOPE="system"
      shift
      ;;
    --user)
      INSTALL_SCOPE="user"
      shift
      ;;
    --deps|--with-deps)
      # Disable the offline default. This may require configured remotes.
      INSTALL_NO_DEPS=0
      shift
      ;;
    --related)
      # Disable the offline default. This may require configured remotes.
      INSTALL_NO_RELATED=0
      shift
      ;;
    --offline)
      # Explicitly force offline-safe defaults.
      INSTALL_NO_DEPS=1
      INSTALL_NO_RELATED=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--user|--system] [--offline] [--deps] [--related]" >&2
      exit 2
      ;;
  esac
done

# Interactive prompt only when invoked with *no arguments*.
if [[ ${ORIG_ARGC} -eq 0 && -t 0 ]]; then
  echo "Install scope?"
  echo "  1) User (no sudo)"
  echo "  2) System-wide (sudo required)"
  read -r -p "Choose [1/2] (default 1): " _choice
  if [[ "${_choice}" == "2" ]]; then
    INSTALL_SCOPE="system"
  fi
fi

# Preflight: the manifest installs Python deps offline with
#   pip install --no-index --find-links=vendor -r requirements.txt
# so every requirement must have a matching wheel in vendor/. Adding a name to
# requirements.txt without dropping its wheel here fails deep inside
# flatpak-builder with an opaque "No matching distribution" error. Catch it here.
REQ_FILE="requirements.txt"
VENDOR_DIR="vendor"
if [[ -f "${REQ_FILE}" ]]; then
  missing=()
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line%%#*}"                       # strip comments
    line="$(echo "${line}" | tr -d '[:space:]')"
    [[ -z "${line}" ]] && continue
    [[ "${line}" == -* ]] && continue        # skip pip flags / -r includes
    name="${line%%[<>=!~;[]*}"               # drop version specifiers/extras/markers
    [[ -z "${name}" ]] && continue
    # Normalize per PEP 503/427: lowercase, runs of -_. collapse to _.
    norm="$(echo "${name}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[-_.]+/_/g')"
    found=0
    shopt -s nullglob
    for whl in "${VENDOR_DIR}"/*.whl; do
      dist="$(basename "${whl}")"
      dist="${dist%%-*}"                      # distribution part of the wheel name
      dnorm="$(echo "${dist}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[-_.]+/_/g')"
      if [[ "${dnorm}" == "${norm}" ]]; then found=1; break; fi
    done
    shopt -u nullglob
    [[ ${found} -eq 0 ]] && missing+=("${name}")
  done < "${REQ_FILE}"

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: offline build installs from '${VENDOR_DIR}/' (pip --no-index), but no" >&2
    echo "matching wheel was found for these '${REQ_FILE}' entries:" >&2
    for m in "${missing[@]}"; do echo "  - ${m}" >&2; done
    echo >&2
    echo "Add the wheel(s), e.g.:" >&2
    echo "  python3 -m pip download ${missing[*]} --only-binary=:all: --no-deps -d ${VENDOR_DIR}/" >&2
    exit 1
  fi
  echo "Preflight OK: every '${REQ_FILE}' entry has a wheel in '${VENDOR_DIR}/'."
fi

echo "Building ${APP_ID} from ${MANIFEST} (install scope: ${INSTALL_SCOPE})..."

mkdir -p "${DISTDIR}"

# Build into the local repo. Avoid `flatpak-builder --install`, because that may
# attempt to resolve runtimes via configured remotes.
flatpak-builder \
  --force-clean \
  --repo="${REPO_DIR}" \
  "${BUILDDIR}" \
  "${MANIFEST}"

echo
echo "Bundling to ${BUNDLE_PATH}..."

flatpak build-bundle \
  "${REPO_DIR}" \
  "${BUNDLE_PATH}" \
  "${APP_ID}"

INSTALL_ARGS=(--bundle --reinstall -y)
if [[ ${INSTALL_NO_DEPS} -eq 1 ]]; then
  INSTALL_ARGS+=(--no-deps)
fi
if [[ ${INSTALL_NO_RELATED} -eq 1 ]]; then
  INSTALL_ARGS+=(--no-related)
fi

echo
if [[ "${INSTALL_SCOPE}" == "system" ]]; then
  echo "Installing system-wide from bundle. This requires sudo."
  echo
  echo "Run this command:"
  echo "  sudo flatpak install --system ${INSTALL_ARGS[*]} ${BUNDLE_PATH}"
  echo
  if [[ -t 0 ]]; then
    read -r -p "Run it now via sudo? [y/N]: " _run_sudo
    if [[ "${_run_sudo}" == "y" || "${_run_sudo}" == "Y" ]]; then
      sudo flatpak install --system "${INSTALL_ARGS[@]}" "${BUNDLE_PATH}"
    fi
  fi
else
  echo "Installing per-user from bundle (no sudo)..."
  echo "  flatpak install --user ${INSTALL_ARGS[*]} ${BUNDLE_PATH}"
  flatpak install --user "${INSTALL_ARGS[@]}" "${BUNDLE_PATH}"
fi

echo
if [[ ${INSTALL_NO_DEPS} -eq 1 || ${INSTALL_NO_RELATED} -eq 1 ]]; then
  echo "Note: offline-safe install flags used:"
  [[ ${INSTALL_NO_DEPS} -eq 1 ]] && echo "  - --no-deps"
  [[ ${INSTALL_NO_RELATED} -eq 1 ]] && echo "  - --no-related"
  echo "If the app fails to run, install the required runtime(s) from your approved local repo/media."
fi

echo
echo "Done."
echo
echo "Bundle created at:"
echo "  ${BUNDLE_PATH}"
echo
echo "Run installed build with:"
echo "  flatpak run ${APP_ID}"
