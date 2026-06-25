#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# Install RitterRadar into the virtual environment.
# Prefer 'prepare.sh' for a first-time setup — this script only installs
# (or re-installs) the Python package and its dependencies.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV="${PROJECT_ROOT}/.venv"
PIP="${VENV}/bin/pip"

if [[ ! -d "${VENV}" ]]; then
    echo "==> Creating virtual environment in .venv/ ..."
    python3 -m venv "${VENV}"
fi

echo "==> Installing RitterRadar (runtime + dev dependencies)..."
"${PIP}" install --upgrade pip --quiet
"${PIP}" install -e "${PROJECT_ROOT}[dev]" --quiet
echo "==> Done. Run 'bash scripts/start_dev.sh' to launch the app."
