#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# Trigger an immediate crawl of all enabled sources via the running RitterRadar API.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/.env"
    set +a
fi

HOST="${RITTERRADAR_HOST:-127.0.0.1}"
PORT="${RITTERRADAR_PORT:-8000}"
BASE_URL="http://${HOST}:${PORT}"

echo "==> Triggering crawl via ${BASE_URL}/api/crawl/trigger ..."
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST "${BASE_URL}/api/crawl/trigger" \
    -H "Content-Type: application/json")

HTTP_BODY=$(echo "${RESPONSE}" | sed -e 's/HTTP_STATUS:.*//')
HTTP_STATUS=$(echo "${RESPONSE}" | grep "HTTP_STATUS:" | sed -e 's/HTTP_STATUS://')

if [[ "${HTTP_STATUS}" == "200" ]]; then
    echo "==> Crawl triggered successfully."
    echo "${HTTP_BODY}" | python3 -m json.tool 2>/dev/null || echo "${HTTP_BODY}"
else
    echo "==> ERROR: API returned HTTP ${HTTP_STATUS}."
    echo "${HTTP_BODY}"
    exit 1
fi
