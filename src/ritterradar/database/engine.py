# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""SQLite engine creation and table initialisation."""

from pathlib import Path

from sqlmodel import SQLModel, create_engine

from ritterradar.config import get_settings

# Populated on first call to get_engine()
_engine = None  # type: ignore[assignment]


def get_engine():  # type: ignore[return]
    """Return the (singleton) SQLAlchemy engine, creating it on first call."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
        _engine = create_engine(
            url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engine


def create_tables() -> None:
    """Create all tables that have not been created yet (idempotent)."""
    import ritterradar.models  # noqa: F401 — side-effect: registers all models

    SQLModel.metadata.create_all(get_engine())
