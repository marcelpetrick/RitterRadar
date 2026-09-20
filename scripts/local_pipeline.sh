#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# Local quality gate for RitterRadar: the same checks CI runs, in one command.
#
# Usage: bash scripts/local_pipeline.sh [--no-browser] [--no-docs]
#
# Stages:
#   1. ruff check          lint
#   2. ruff format --check formatting
#   3. mypy src            strict type check
#   4. pytest              offline suite, fails below 90 % coverage
#   5. browser_test.py     offline Playwright regression run (optional)
#   6. sphinx-build        documentation build (optional)
#
# Exits non-zero as soon as the summary contains a FAIL.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

RUN_BROWSER=1
RUN_DOCS=1
for arg in "$@"; do
    case "$arg" in
        --no-browser) RUN_BROWSER=0 ;;
        --no-docs) RUN_DOCS=0 ;;
        -h|--help)
            sed -n '5,7p' "${BASH_SOURCE[0]}"
            exit 0
            ;;
        *)
            echo "[ERROR] Unknown option: $arg" >&2
            exit 2
            ;;
    esac
done

if [[ -x .venv/bin/python ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

LINT_TARGETS=(src tests scripts/browser_test.py scripts/audit_month.py)
SUMMARY=()
FAILED=0

run_stage() {
    local name="$1"
    shift
    echo
    echo "[INFO] ${name}: $*"
    if "$@"; then
        SUMMARY+=("$(printf '%-20s: PASS' "$name")")
    else
        SUMMARY+=("$(printf '%-20s: FAIL' "$name")")
        FAILED=1
    fi
}

skip_stage() {
    SUMMARY+=("$(printf '%-20s: SKIP %s' "$1" "$2")")
}

run_stage "Lint" ruff check "${LINT_TARGETS[@]}"
run_stage "Format" ruff format --check "${LINT_TARGETS[@]}"
run_stage "Types" mypy src
run_stage "Tests" pytest

if [[ "$RUN_BROWSER" -eq 0 ]]; then
    skip_stage "Browser tests" "disabled via --no-browser"
elif ! python -c "import playwright" >/dev/null 2>&1; then
    skip_stage "Browser tests" "playwright missing: pip install -e '.[browser]'"
else
    run_stage "Browser tests" python scripts/browser_test.py
fi

if [[ "$RUN_DOCS" -eq 0 ]]; then
    skip_stage "Documentation" "disabled via --no-docs"
elif ! command -v sphinx-build >/dev/null 2>&1; then
    skip_stage "Documentation" "sphinx-build missing: pip install -e '.[dev]'"
else
    run_stage "Documentation" sphinx-build -q docs/source docs/_build/html
fi

echo
echo "========== Local Pipeline Summary =========="
printf '%s\n' "${SUMMARY[@]}"
echo "==========================================="

if [[ "$FAILED" -ne 0 ]]; then
    echo "[ERROR] Quality gate failed."
    exit 1
fi
echo "[INFO] Quality gate passed."
