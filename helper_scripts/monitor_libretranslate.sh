#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${1:-libretranslate}"
API_URL="${2:-http://localhost:5000}"

echo "Monitoring LibreTranslate (${CONTAINER_NAME}) at ${API_URL}"
echo "  - Ctrl+C to stop"
echo

while true; do
  # Container status
  status=$(docker inspect -f '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "not-found")
  dt=$(date +'%H:%M:%S')

  # Language count
  lang_count="0"
  lang_list=""
  http_code=$(curl -s -o /tmp/lt_langs.json -w "%{http_code}" "${API_URL}/languages" || echo "000")

  if [ "$http_code" = "200" ]; then
    lang_count=$(jq 'length' /tmp/lt_langs.json 2>/dev/null || echo "0")
    lang_list=$(jq -r 'map(.code) | join(", ")' /tmp/lt_langs.json 2>/dev/null || echo "")
  else
    lang_count="0"
    lang_list="(API not ready; HTTP ${http_code})"
  fi

  printf "%s | container=%-10s | languages=%3s | %s\n" \
    "$dt" "$status" "$lang_count" "$lang_list"

  sleep 10
done
