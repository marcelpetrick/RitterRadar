#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# Drop and recreate the RitterRadar SQLite database.
# WARNING: All stored markets, sources, and crawl history are deleted.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/.env"
    set +a
fi

DB_PATH="${RITTERRADAR_DB_PATH:-${PROJECT_ROOT}/data/ritterradar.db}"

echo "==> WARNING: This will permanently delete all data in '${DB_PATH}'."
read -rp "    Type 'yes' to confirm: " CONFIRM

if [[ "${CONFIRM}" != "yes" ]]; then
    echo "==> Aborted."
    exit 0
fi

if [[ -f "${DB_PATH}" ]]; then
    rm -f "${DB_PATH}" "${DB_PATH}-wal" "${DB_PATH}-shm"
    echo "==> Deleted '${DB_PATH}'."
fi

mkdir -p "$(dirname "${DB_PATH}")"
echo "==> Running migrations to recreate schema..."
cd "${PROJECT_ROOT}"
alembic upgrade head
echo "==> Database reset complete."
