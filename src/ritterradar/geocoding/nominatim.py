# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Nominatim geocoder with SQLite-backed cache and rate limiting."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import Session, select

from ritterradar.database.engine import get_engine
from ritterradar.models.geocoding_cache import GeocodingCache

logger = logging.getLogger(__name__)

# Nominatim ToS: maximum 1 request per second
_RATE_LIMIT_SECONDS = 1.1
_last_request_time: float = 0.0
_rate_limit_lock = asyncio.Lock()


@dataclass
class GeoResult:
    """Result of a successful geocoding lookup."""

    latitude: float
    longitude: float
    display_name: str
    uncertain: bool


async def geocode(query: str, user_agent: str) -> GeoResult | None:
    """Geocode *query* using Nominatim with cache and rate limiting.

    Returns ``None`` when the address cannot be resolved at all.
    Sets ``uncertain=True`` when the result confidence is low
    (importance < 0.4 or result type is too coarse).
    """
    normalised = query.strip().lower()
    if not normalised:
        return None

    cached = _cache_get(normalised)
    if cached is not None:
        return cached

    result = await _nominatim_lookup(query, user_agent)
    if result is not None:
        _cache_set(normalised, result)
    return result


def _cache_get(normalised_query: str) -> GeoResult | None:
    with Session(get_engine()) as session:
        row = session.exec(
            select(GeocodingCache).where(GeocodingCache.query == normalised_query)
        ).first()
        if row is None:
            return None
        return GeoResult(
            latitude=row.latitude,
            longitude=row.longitude,
            display_name=row.display_name,
            uncertain=row.uncertain,
        )


def _cache_set(normalised_query: str, result: GeoResult) -> None:
    with Session(get_engine()) as session:
        existing = session.exec(
            select(GeocodingCache).where(GeocodingCache.query == normalised_query)
        ).first()
        if existing is None:
            session.add(
                GeocodingCache(
                    query=normalised_query,
                    latitude=result.latitude,
                    longitude=result.longitude,
                    display_name=result.display_name,
                    uncertain=result.uncertain,
                    cached_at=datetime.now(UTC),
                )
            )
        else:
            existing.latitude = result.latitude
            existing.longitude = result.longitude
            existing.display_name = result.display_name
            existing.uncertain = result.uncertain
            existing.cached_at = datetime.now(UTC)
            session.add(existing)
        session.commit()


async def _nominatim_lookup(query: str, user_agent: str) -> GeoResult | None:
    global _last_request_time

    async with _rate_limit_lock:
        now = asyncio.get_event_loop().time()
        wait = _RATE_LIMIT_SECONDS - (now - _last_request_time)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_time = asyncio.get_event_loop().time()

    try:
        # Run the blocking geopy call in a thread pool
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _blocking_lookup(query, user_agent)
        )
        return result
    except Exception:
        logger.exception("Nominatim lookup failed for query %r", query)
        return None


def _blocking_lookup(query: str, user_agent: str) -> GeoResult | None:
    from geopy.geocoders import Nominatim  # type: ignore[import-untyped]

    geolocator = Nominatim(user_agent=user_agent)
    location = geolocator.geocode(  # type: ignore[union-attr]
        query, exactly_one=True, language="de", addressdetails=False
    )
    if location is None:
        return None

    importance: float = getattr(location, "importance", None) or 0.0
    raw: dict = getattr(location, "raw", {})
    result_type: str = raw.get("type", "")

    # Mark uncertain if importance is low or the result is too coarse
    coarse_types = {"country", "state", "county", "region"}
    uncertain = importance < 0.4 or result_type in coarse_types

    return GeoResult(
        latitude=location.latitude,
        longitude=location.longitude,
        display_name=str(location.address),
        uncertain=uncertain,
    )
