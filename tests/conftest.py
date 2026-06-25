# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Shared pytest fixtures."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Point config away from any real file before app code loads
os.environ.setdefault("RITTERRADAR_DB_PATH", ":memory:")
os.environ.setdefault("RITTERRADAR_SOURCES_FILE", "config/sources.yaml")
os.environ.setdefault("RITTERRADAR_GEOCODER_EMAIL", "test@example.com")
os.environ.setdefault("RITTERRADAR_WORKERS", "0")  # no workers in tests


@pytest.fixture(scope="session", autouse=True)
def test_engine():
    """Single shared in-memory SQLite engine for the test session.

    StaticPool forces all connections to share the same in-memory database,
    so data written by one session is visible to another.
    """
    import ritterradar.models  # noqa: F401 — register all models

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    import ritterradar.database.engine as eng_mod
    eng_mod._engine = engine
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def session(test_engine) -> Generator[Session, None, None]:
    """Database session that commits data so the TestClient can see it."""
    with Session(test_engine) as s:
        yield s
        # Don't rollback here — tests that write data via session need it visible


@pytest.fixture(scope="session")
def client(test_engine) -> Generator[TestClient, None, None]:
    from ritterradar.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
