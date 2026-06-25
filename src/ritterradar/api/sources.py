# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Sources API — list configured crawl sources and their status."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from ritterradar.database.session import get_session
from ritterradar.models.source import Source

router = APIRouter(prefix="/api/sources", tags=["sources"])


class SourceOut(BaseModel):
    id: int
    name: str
    base_url: str
    adapter_name: str
    enabled: bool
    last_crawled_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None


@router.get("", response_model=list[SourceOut])
async def list_sources(
    session: Annotated[Session, Depends(get_session)],
) -> list[SourceOut]:
    """Return all configured sources with their last crawl status."""
    sources = session.exec(select(Source).order_by(Source.name)).all()  # type: ignore[arg-type]
    return [
        SourceOut(
            id=s.id or 0,
            name=s.name,
            base_url=s.base_url,
            adapter_name=s.adapter_name,
            enabled=s.enabled,
            last_crawled_at=s.last_crawled_at,
            last_success_at=s.last_success_at,
            last_error=s.last_error,
        )
        for s in sources
    ]
