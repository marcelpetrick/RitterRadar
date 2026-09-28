#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
umask 077
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"
[[ ! -f .env ]] || chmod 600 .env
exec "${PROJECT_ROOT}/.venv/bin/ritterradar"
