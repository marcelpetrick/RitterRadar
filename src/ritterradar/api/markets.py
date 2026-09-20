# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Markets API — listing, filtering, and visibility control."""

from datetime import UTC, date, datetime
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from ritterradar.database.session import get_session
from ritterradar.event_scope import exclusion_reason
from ritterradar.geocoding.haversine import distance_km
from ritterradar.market_identity import current_source_records
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
    date_from: date | None = Query(default=None, description="First day to include (YYYY-MM-DD)"),
    date_to: date | None = Query(default=None, description="Last day to include (YYYY-MM-DD)"),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, ge=0),
    include_hidden: bool = Query(default=False),
    market_type: list[str] = Query(default=[]),
) -> list[MarketOut]:
    """Return markets matching the given filters."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    if (lat is None) != (lon is None):
        raise HTTPException(status_code=422, detail="lat and lon must be provided together")
    if radius_km is not None and (lat is None or lon is None):
        raise HTTPException(status_code=422, detail="radius_km requires lat and lon")

    stmt = select(Market).where(Market.end_date >= Market.start_date)
    markets = session.exec(stmt.order_by(cast(Any, Market.start_date))).all()

    results: list[MarketOut] = []
    # Resolve corrected source dates before filtering: otherwise an old record
    # can reappear when its replacement moved outside the requested month.
    for m in current_source_records(list(markets)):
        if (m.hidden and not include_hidden) or (market_type and m.market_type not in market_type):
            continue
        if (date_from and m.end_date < date_from) or (date_to and m.start_date > date_to):
            continue
        if exclusion_reason(m.name, m.source_name):
            continue
        dist: float | None = None
        market_lat = m.latitude
        market_lon = m.longitude
        if lat is not None and lon is not None:
            # A spatial result must always have a meaningful distance. Markets
            # without coordinates remain available to non-spatial queries.
            if market_lat is None or market_lon is None:
                continue
            dist = round(distance_km(lat, lon, market_lat, market_lon), 1)
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
