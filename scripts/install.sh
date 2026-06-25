#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# Install RitterRadar and all dependencies into the current Python environment.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==> Installing RitterRadar (runtime + dev dependencies)..."
pip install -e "${PROJECT_ROOT}[dev]"
echo "==> Done. Run 'scripts/start_dev.sh' to launch the app."
