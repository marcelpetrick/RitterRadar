# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Markets API — listing, filtering, and visibility control."""

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from ritterradar.database.session import get_session
from ritterradar.geocoding.haversine import distance_km
from ritterradar.models.market import Market

router = APIRouter(prefix="/api/markets", tags=["markets"])


class MarketOut(BaseModel):
    """Market record returned by the API."""

    id: int
    name: str
    market_type: str
    start_date: date
    end_date: date
    address: str | None
    city: str | None
    postal_code: str | None
    country: str
    latitude: float | None
    longitude: float | None
    geocode_uncertain: bool
    program_text: str | None
    source_name: str
    source_url: str
    hidden: bool
    confidence_score: float
    created_at: datetime
    distance_km: float | None = None


@router.get("", response_model=list[MarketOut])
async def list_markets(
    session: Annotated[Session, Depends(get_session)],
    date_from: date | None = Query(default=None, description="Earliest start_date (YYYY-MM-DD)"),
    date_to: date | None = Query(default=None, description="Latest start_date (YYYY-MM-DD)"),
    lat: float | None = Query(default=None, description="Home latitude for distance filter"),
    lon: float | None = Query(default=None, description="Home longitude for distance filter"),
    radius_km: float | None = Query(default=None, description="Max straight-line distance in km"),
    include_hidden: bool = Query(default=False),
    market_type: list[str] = Query(default=[]),
) -> list[MarketOut]:
    """Return markets matching the given filters."""
    stmt = select(Market)
    if not include_hidden:
        stmt = stmt.where(Market.hidden == False)  # noqa: E712
    if date_from:
        stmt = stmt.where(Market.start_date >= date_from)
    if date_to:
        stmt = stmt.where(Market.start_date <= date_to)
    if market_type:
        stmt = stmt.where(Market.market_type.in_(market_type))  # type: ignore[union-attr]

    markets = session.exec(stmt.order_by(Market.start_date)).all()  # type: ignore[arg-type]

    results: list[MarketOut] = []
    for m in markets:
        dist: float | None = None
        coords_ok = (
            lat is not None
            and lon is not None
            and m.latitude is not None
            and m.longitude is not None
        )
        if coords_ok:
            dist = round(distance_km(lat, lon, m.latitude, m.longitude), 1)
            if radius_km is not None and dist > radius_km:
                continue

        results.append(
            MarketOut(
                id=m.id or 0,
                name=m.name,
                market_type=m.market_type,
                start_date=m.start_date,
                end_date=m.end_date,
                address=m.address,
                city=m.city,
                postal_code=m.postal_code,
                country=m.country,
                latitude=m.latitude,
                longitude=m.longitude,
                geocode_uncertain=m.geocode_uncertain,
                program_text=m.program_text,
                source_name=m.source_name,
                source_url=m.source_url,
                hidden=m.hidden,
                confidence_score=m.confidence_score,
                created_at=m.created_at,
                distance_km=dist,
            )
        )

    return results


@router.post("/{market_id}/hide")
async def toggle_hide(
    market_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, object]:
    """Toggle the hidden flag for a market."""
    market = session.get(Market, market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="Market not found")
    market.hidden = not market.hidden
    market.updated_at = datetime.now(UTC)
    session.add(market)
    return {"id": market_id, "hidden": market.hidden}
