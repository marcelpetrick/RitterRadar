#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# Start the RitterRadar production server.
# Reads configuration from .env if present.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load .env if it exists
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/.env"
    set +a
fi

HOST="${RITTERRADAR_HOST:-127.0.0.1}"
PORT="${RITTERRADAR_PORT:-8000}"

echo "==> Starting RitterRadar at http://${HOST}:${PORT}"
echo "==> Open your browser at http://${HOST}:${PORT}"
echo "==> Press Ctrl+C to stop."

cd "${PROJECT_ROOT}"
exec uvicorn ritterradar.main:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --log-level "${RITTERRADAR_LOG_LEVEL:-info}"
