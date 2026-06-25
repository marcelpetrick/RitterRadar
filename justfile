# RitterRadar — just task runner
# Install just: https://just.systems/
# Or use the scripts/ shell scripts directly (no just required).

# Install all dependencies (runtime + dev) into the current environment
install:
    pip install -e ".[dev]"

# Start development server with auto-reload
dev:
    uvicorn ritterradar.main:app --host 127.0.0.1 --port 8000 --reload --log-level debug

# Start production server
start:
    uvicorn ritterradar.main:app --host "${RITTERRADAR_HOST:-127.0.0.1}" --port "${RITTERRADAR_PORT:-8000}"

# Run all tests with coverage
test:
    pytest

# Run tests without coverage (fast)
test-fast:
    pytest --no-cov -x

# Lint with ruff
lint:
    ruff check src tests

# Format with ruff
fmt:
    ruff format src tests

# Type-check with mypy
types:
    mypy src

# Build Sphinx HTML documentation
docs:
    sphinx-build docs/source docs/_build/html

# Apply all pending Alembic migrations
migrate:
    alembic upgrade head

# Create a new Alembic migration (pass description: just makemig "add foo column")
makemig description:
    alembic revision --autogenerate -m "{{description}}"

# Reset the database (drop and recreate)
reset-db:
    bash scripts/reset_db.sh

# Trigger a crawl via the running API
crawl:
    bash scripts/trigger_crawl.sh

# Run full CI pipeline: lint + types + tests
ci:
    just lint && just types && just test
