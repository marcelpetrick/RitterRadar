# syntax=docker/dockerfile:1
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# RitterRadar container image.
#
# Build:  docker build -t ritterradar .
# Run:    docker run --rm -p 127.0.0.1:8000:8000 -v ritterradar-data:/app/data ritterradar

ARG PYTHON_IMAGE=python:3.14.7-slim-trixie

# ── Stage 1: build the virtual environment ───────────────────────────
FROM ${PYTHON_IMAGE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
RUN python -m venv /opt/venv

# Install the pinned runtime dependencies first so this layer stays cached
# as long as pyproject.toml is unchanged.
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" \
        > requirements.txt \
    && /opt/venv/bin/pip install --only-binary=:all: -r requirements.txt

COPY README.md LICENSE ./
COPY src ./src
RUN /opt/venv/bin/pip install --no-deps .

# ── Stage 2: minimal runtime image ───────────────────────────────────
FROM ${PYTHON_IMAGE} AS runtime

LABEL org.opencontainers.image.title="RitterRadar" \
      org.opencontainers.image.description="Discover German medieval markets, Renaissance festivals, and Viking fairs on an interactive map" \
      org.opencontainers.image.source="https://github.com/marcelpetrick/RitterRadar" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      org.opencontainers.image.authors="Marcel Petrick <mail@marcelpetrick.it>"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    RITTERRADAR_HOST=0.0.0.0 \
    RITTERRADAR_PORT=8000 \
    RITTERRADAR_DB_PATH=/app/data/ritterradar.db \
    RITTERRADAR_SOURCES_FILE=/app/config/sources.yaml

RUN groupadd --system --gid 10001 ritter \
    && useradd --system --uid 10001 --gid ritter --home-dir /app --no-create-home \
        --shell /usr/sbin/nologin ritter

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY config ./config
COPY alembic.ini ./
COPY alembic ./alembic
RUN mkdir -p /app/data && chown ritter:ritter /app/data

USER 10001:10001
VOLUME ["/app/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('RITTERRADAR_PORT', '8000') + '/health', timeout=4)"]

CMD ["ritterradar"]
