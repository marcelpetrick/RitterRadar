# Repository guidance for Codex and Claude Code

RitterRadar is a Python 3.12–3.14 FastAPI/SQLite application. Keep changes
focused, preserve the offline test suite, and use conventional commit subjects
(`type(scope): summary`). The project history uses small commits grouped by
feature, fix, tests, docs, or release work.

## Local workflow

- Read `README.md`, `documents/00_VISION.md`, `docs/architecture.md`, and the
  relevant adapter/API tests before changing behavior.
- Set up the environment with `bash scripts/prepare.sh`; this creates `.venv`
  and applies database migrations.
- Run `bash scripts/local_pipeline.sh` (or `just ci`) before proposing a
  change. It runs Ruff lint/format checks, strict mypy, pytest with the 98%
  coverage gate, browser regression tests, and Sphinx documentation when the
  optional tools are installed. CI additionally runs security scans.
- Keep measured line coverage at or above 98% by testing meaningful behavior,
  including failure paths; do not weaken the gate or add tests that merely
  mirror implementation details.
- Useful focused checks: `pytest --no-cov -x -q`, `ruff check src tests`,
  `ruff format --check src tests`, `mypy src`, and
  `sphinx-build -W --keep-going -q docs/source docs/_build/html`.
- Browser regression tests use Playwright and run without external network
  access: `python scripts/browser_test.py`.

## Application and security constraints

- Keep native server binding on loopback by default. Network access requires
  configured authentication; add any intentional request Host to
  `RITTERRADAR_ALLOWED_HOSTS` explicitly. Preserve request-origin checks,
  security headers, bounded request/crawler work, and safe outbound HTTP
  destination validation.
- Do not put personal home-location values or secrets in logs, fixtures,
  documentation, or command output. `.env`, runtime data, logs, build outputs,
  and virtual environments are local state and must not be committed.
- Keep tests deterministic and offline. Stub external geocoding and HTTP; do
  not make live upstream requests from unit tests.
- API or deployment behavior changes must be reflected in `README.md`,
  `.env.example`, and `CHANGELOG.md` as appropriate.

## Versioning and release

- `pyproject.toml` is the package version source of truth. Keep README and
  changelog aligned with the intended release.
- Use Semantic Versioning. The `vX.Y.Z` tag must match `pyproject.toml`, and
  the version needs a `CHANGELOG.md` entry before release workflows pass.
- Follow the release workflow in `README.md`: complete CI and image checks,
  commit the version/changelog update, push the branch, then push the matching
  annotated tag. Never claim a release or security scan passed until its
  workflow result confirms it.
