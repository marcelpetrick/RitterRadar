#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# One-time setup script for RitterRadar on Arch/Manjaro (or any system
# that enforces PEP 668 externally-managed-environment).
#
# Usage: bash scripts/prepare.sh
#
# What it does:
#   1. Creates a Python virtual environment in .venv/
#   2. Installs all runtime + dev dependencies into that venv
#   3. Copies .env.example → .env if .env does not already exist
#   4. Creates the data/ directory
#   5. Runs the initial database migration
#   6. Prints a "you're ready" banner with next steps
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV="${PROJECT_ROOT}/.venv"
PY="${VENV}/bin/python"
PIP="${VENV}/bin/pip"

cd "${PROJECT_ROOT}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║           ⚔  RitterRadar — Setup Wizard  ⚔          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: virtual environment ───────────────────────────────────────
if [[ -d "${VENV}" ]]; then
    echo "✓  Virtual environment already exists at .venv/"
else
    echo "→  Creating virtual environment in .venv/ ..."
    python3 -m venv "${VENV}"
    echo "✓  Virtual environment created."
fi

# ── Step 2: install dependencies ─────────────────────────────────────
echo "→  Installing RitterRadar and all dependencies ..."
"${PIP}" install --upgrade pip --quiet
"${PIP}" install -e ".[dev]" --quiet
echo "✓  Dependencies installed."

# ── Step 3: .env file ────────────────────────────────────────────────
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    echo "✓  .env already exists — keeping it."
else
    cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
    echo "✓  .env created from .env.example."
    echo "   ➜  Edit .env and set RITTERRADAR_GEOCODER_EMAIL to your e-mail address."
    echo "      (Required by Nominatim / OpenStreetMap terms of service.)"
fi

# ── Step 4: data directory ────────────────────────────────────────────
mkdir -p "${PROJECT_ROOT}/data"
echo "✓  data/ directory ready."

# ── Step 5: database migration ───────────────────────────────────────
echo "→  Running database migrations ..."
"${VENV}/bin/alembic" upgrade head
echo "✓  Database schema up to date."

# ── Step 6: banner ───────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✓  RitterRadar is ready!                          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Start the app:"
echo "    bash scripts/start_dev.sh        (development, auto-reload)"
echo "    bash scripts/start.sh            (production)"
echo ""
echo "  Then open: http://127.0.0.1:8000"
echo ""
echo "  Other commands:"
echo "    bash scripts/trigger_crawl.sh   — trigger a crawl via API"
echo "    bash scripts/crawl_status.sh    — check crawl status"
echo "    bash scripts/reset_db.sh        — wipe and recreate database"
echo ""
