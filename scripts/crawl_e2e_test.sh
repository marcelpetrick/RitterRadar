#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# End-to-end crawler test — runs each enabled adapter standalone,
# no database or server needed.
#
# Usage:
#   bash scripts/crawl_e2e_test.sh              # all enabled adapters
#   bash scripts/crawl_e2e_test.sh spectaculum  # specific adapter(s)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV="${PROJECT_ROOT}/.venv"

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a; source "${PROJECT_ROOT}/.env"; set +a
fi

PY="${VENV}/bin/python3"
if [[ ! -x "${PY}" ]]; then
    PY="python3"
fi

exec "${PY}" "${SCRIPT_DIR}/crawl_e2e_test.py" "$@"
