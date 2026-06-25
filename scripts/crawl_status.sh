#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# Show current crawl queue status from the running RitterRadar API.
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

echo "==> Fetching crawl status from http://${HOST}:${PORT}/api/crawl/status ..."
curl -s "http://${HOST}:${PORT}/api/crawl/status" | python3 -m json.tool
