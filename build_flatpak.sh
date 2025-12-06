#!/usr/bin/env bash
set -euo pipefail

APP_ID="uk.codecrafter.FancyClock"
RUNTIME="org.freedesktop.Platform"
RUNTIME_VERSION="23.08"
SDK="org.freedesktop.Sdk"
BRANCH="master"

FLATPAK_DIR="flatpak"
BUILD_DIR="${FLATPAK_DIR}/build-dir"
MANIFEST="${FLATPAK_DIR}/${APP_ID}.yml"
DESKTOP_FILE="${FLATPAK_DIR}/${APP_ID}.desktop"
WRAPPER_SCRIPT="${FLATPAK_DIR}/fancyclock-wrapper.sh"
BUNDLE_FILE="${FLATPAK_DIR}/${APP_ID}.flatpak"
MEDIA_DIR="media"      # <--- NEW: media directory in repo root

##############################################
# Helpers                                    #
##############################################

# Convert bytes -> MB with one decimal place
bytes_to_mb() {
    local bytes="${1:-0}"
    awk -v b="$bytes" 'BEGIN { printf "%.1f", (b/1048576) }'
}

# Live progress: repo object count + bundle size + throughput
live_progress() {
    local pid="$1"
    local start_time
    start_time=$(date +%s)

    local prev_time="$start_time"
    local prev_size=0

    while kill -0 "$pid" 2>/dev/null; do
        # Repo object count
        local obj_count
        obj_count=$(find "${FLATPAK_DIR}/repo/objects" -type f 2>/dev/null | wc -l)

        # Bundle size
        local size_bytes=0
        if [ -f "$BUNDLE_FILE" ]; then
            size_bytes=$(stat -c%s "$BUNDLE_FILE" 2>/dev/null || echo 0)
        fi

        local now
        now=$(date +%s)
        local dt=$(( now - prev_time ))
        if [ "$dt" -le 0 ]; then
            dt=1
        fi

        local elapsed=$(( now - start_time ))
        if [ "$elapsed" -le 0 ]; then
            elapsed=1
        fi

        local avg_rate_bytes=$(( size_bytes / elapsed ))

        if [ "$size_bytes" -lt "$prev_size" ]; then
            prev_size=$size_bytes
        fi
        local delta_bytes=$(( size_bytes - prev_size ))
        if [ "$delta_bytes" -lt 0 ]; then
            delta_bytes=0
        fi
        local inst_rate_bytes=$(( delta_bytes / dt ))

        local size_mb
        size_mb=$(bytes_to_mb "$size_bytes")
        local inst_mb_s
        inst_mb_s=$(bytes_to_mb "$inst_rate_bytes")
        local avg_mb_s
        avg_mb_s=$(bytes_to_mb "$avg_rate_bytes")

        printf "\rRepo objs: %6s | Bundle: %7s MB | Rate: %5s MB/s (avg %5s MB/s) " \
            "$obj_count" "$size_mb" "$inst_mb_s" "$avg_mb_s"

        prev_time="$now"
        prev_size="$size_bytes"

        sleep 0.5
    done

    # Final snapshot once process exits
    local final_obj_count
    final_obj_count=$(find "${FLATPAK_DIR}/repo/objects" -type f 2>/dev/null | wc -l)

    local final_size_bytes=0
    if [ -f "$BUNDLE_FILE" ]; then
        final_size_bytes=$(stat -c%s "$BUNDLE_FILE" 2>/dev/null || echo 0)
    fi
    local final_size_mb
    final_size_mb=$(bytes_to_mb "$final_size_bytes")

    local end
    end=$(date +%s)
    local total_elapsed=$(( end - start_time ))
    if [ "$total_elapsed" -le 0 ]; then
        total_elapsed=1
    fi
    local final_avg_rate_bytes=$(( final_size_bytes / total_elapsed ))
    local final_avg_mb_s
    final_avg_mb_s=$(bytes_to_mb "$final_avg_rate_bytes")

    printf "\rRepo objs: %6s | Bundle: %7s MB | Rate:  done   (avg %5s MB/s) \n" \
        "$final_obj_count" "$final_size_mb" "$final_avg_mb_s"
}

##############################################
# Basic checks                               #
##############################################
echo "==> Checking for requirements.txt ..."
if [ ! -f requirements.txt ]; then
  echo "ERROR: requirements.txt not found in current directory."
  exit 1
fi

echo "==> Checking for media directory (${MEDIA_DIR}) ..."
if [ ! -d "${MEDIA_DIR}" ]; then
  echo "ERROR: media directory '${MEDIA_DIR}' not found in current directory."
  exit 1
fi

mkdir -p "$FLATPAK_DIR"

##############################################
# Desktop file                               #
##############################################
cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=FancyClock
Comment=Fancy multi-timezone clock
Exec=fancyclock
Icon=${APP_ID}
Categories=Utility;Clock;Qt;
Terminal=false
StartupNotify=true
EOF

##############################################
# Wrapper script                             #
##############################################
cat > "${WRAPPER_SCRIPT}" <<'EOF'
#!/usr/bin/env bash
exec python3 /app/FancyClock/main.py "$@"
EOF
chmod +x "${WRAPPER_SCRIPT}"

##############################################
# Flatpak manifest                           #
##############################################
cat > "${MANIFEST}" <<EOF
app-id: ${APP_ID}
runtime: ${RUNTIME}
runtime-version: '${RUNTIME_VERSION}'
sdk: ${SDK}

command: fancyclock

finish-args:
  - --share=ipc
  - --socket=x11
  - --socket=wayland
  - --device=dri
  - --env=PYTHONPATH=/app/FancyClock

modules:
  - name: FancyClock
    buildsystem: simple

    build-options:
      build-args:
        - --share=network

    build-commands:
      - install -d /app/FancyClock
      - cp -a . /app/FancyClock
      - cp -a ${MEDIA_DIR} /app/FancyClock/
      - pip3 install --no-cache-dir --prefix=/app -r requirements.txt
      - install -D flatpak/fancyclock-wrapper.sh /app/bin/fancyclock
      - chmod +x /app/bin/fancyclock
      - install -D flatpak/${APP_ID}.desktop /app/share/applications/${APP_ID}.desktop
      - install -D clock.png /app/share/icons/hicolor/256x256/apps/${APP_ID}.png

    sources:
      - type: dir
        path: ..
EOF

echo "==> Building Flatpak (with network access for pip) ..."
flatpak-builder --user --force-clean --repo="${FLATPAK_DIR}/repo" "${BUILD_DIR}" "${MANIFEST}"

##############################################
# Create bundle WITH LIVE METRICS            #
##############################################
echo "==> Creating .flatpak bundle with live metrics..."
rm -f "${BUNDLE_FILE}"

flatpak build-bundle \
  "${FLATPAK_DIR}/repo" \
  "${BUNDLE_FILE}" \
  "${APP_ID}" \
  "${BRANCH}" &

BUNDLE_PID=$!

live_progress "$BUNDLE_PID"
wait "$BUNDLE_PID"

echo
echo "==> Bundle created at: ${BUNDLE_FILE}"
echo "Install with:"
echo "  flatpak install ${BUNDLE_FILE}"
echo "Run with:"
echo "  flatpak run ${APP_ID}"
echo
