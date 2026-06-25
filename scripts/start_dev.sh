#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# Start RitterRadar in development mode with auto-reload and debug logging.
# Uses .venv/ automatically if it exists (Arch/Manjaro PEP 668 safe).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV="${PROJECT_ROOT}/.venv"

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/.env"
    set +a
fi

UVICORN="${VENV}/bin/uvicorn"
[[ -x "${UVICORN}" ]] || UVICORN="uvicorn"

if [[ "${UVICORN}" == "uvicorn" ]] && ! command -v uvicorn &>/dev/null; then
    echo "ERROR: uvicorn not found. Run 'bash scripts/prepare.sh' first." >&2
    exit 1
fi

HOST="${RITTERRADAR_HOST:-127.0.0.1}"
PORT="${RITTERRADAR_PORT:-8000}"

echo "==> Starting RitterRadar [DEV] at http://${HOST}:${PORT}"
echo "==> Auto-reload enabled — file changes restart the server automatically."
echo "==> Press Ctrl+C to stop."

cd "${PROJECT_ROOT}"
exec "${UVICORN}" ritterradar.main:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --reload \
    --reload-dir src \
    --log-level debug
