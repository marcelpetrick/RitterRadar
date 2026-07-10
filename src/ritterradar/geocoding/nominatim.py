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
from typing import Any, cast

from sqlmodel import Session, select

from ritterradar.database.engine import get_engine
from ritterradar.models.geocoding_cache import GeocodingCache

logger = logging.getLogger(__name__)

GeoQuery = str | dict[str, str]

_COUNTRY_DISPLAY_NAMES: dict[str, tuple[str, ...]] = {
    "at": ("österreich", "austria"),
    "ch": ("schweiz", "suisse", "svizzera", "switzerland"),
    "de": ("deutschland", "germany"),
    "lu": ("luxembourg", "luxemburg", "lëtzebuerg"),
    "nl": ("nederland", "niederlande", "netherlands"),
}

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


async def geocode(
    query: str,
    user_agent: str,
    *,
    country_code: str | None = None,
    postal_code: str | None = None,
    city: str | None = None,
) -> GeoResult | None:
    """Geocode *query* using Nominatim with cache and rate limiting.

    Returns ``None`` when the address cannot be resolved at all.
    Sets ``uncertain=True`` when the result confidence is low
    (importance < 0.4 or result type is too coarse).
    """
    cache_key = _cache_key(query, country_code, postal_code, city)
    if not cache_key:
        return None

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    legacy_key = query.strip().lower()
    if cache_key != legacy_key:
        legacy = _cache_get(legacy_key)
        if legacy is not None and _legacy_result_matches(legacy, country_code, postal_code):
            _cache_set(cache_key, legacy)
            return legacy

    lookup_query = _structured_query(postal_code, city) or query
    result = await _nominatim_lookup(
        lookup_query,
        user_agent,
        country_code=country_code,
        postal_code=postal_code,
    )
    if result is None and postal_code and city:
        # Some locality names are ambiguous even alongside a postal code.
        # A validated postal centroid is safer than accepting the wrong city.
        result = await _nominatim_lookup(
            {"postalcode": postal_code.strip()},
            user_agent,
            country_code=country_code,
            postal_code=postal_code,
        )
    if result is not None:
        _cache_set(cache_key, result)
    return result


def _cache_key(
    query: str,
    country_code: str | None,
    postal_code: str | None,
    city: str | None,
) -> str:
    normalised_query = query.strip().lower()
    if not normalised_query:
        return ""
    if country_code is None and postal_code is None and city is None:
        return normalised_query
    return "|".join(
        (
            "market-v2",
            (country_code or "").strip().lower(),
            _normalise_postal_code(postal_code),
            (city or "").strip().lower(),
            normalised_query,
        )
    )


def _structured_query(postal_code: str | None, city: str | None) -> dict[str, str]:
    query: dict[str, str] = {}
    if postal_code:
        query["postalcode"] = postal_code.strip()
    if city:
        query["city"] = city.strip()
    return query


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


async def _nominatim_lookup(
    query: GeoQuery,
    user_agent: str,
    *,
    country_code: str | None = None,
    postal_code: str | None = None,
) -> GeoResult | None:
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
            None,
            lambda: _blocking_lookup(
                query,
                user_agent,
                country_code=country_code,
                postal_code=postal_code,
            ),
        )
        return result
    except Exception:
        logger.exception("Nominatim lookup failed for query %r", query)
        return None


def _blocking_lookup(
    query: GeoQuery,
    user_agent: str,
    *,
    country_code: str | None = None,
    postal_code: str | None = None,
) -> GeoResult | None:
    from geopy.geocoders import Nominatim

    geolocator = Nominatim(user_agent=user_agent)
    location = geolocator.geocode(
        query,
        exactly_one=True,
        language="de",
        addressdetails=True,
        country_codes=country_code.lower() if country_code else None,
    )
    if location is None:
        return None

    importance: float = getattr(location, "importance", None) or 0.0
    raw: dict[str, Any] = getattr(location, "raw", {})
    if not _matches_expected_location(raw, country_code, postal_code):
        logger.warning("Rejected mismatched Nominatim result for query %r", query)
        return None
    result_type: str = raw.get("type", "")

    # Mark uncertain if importance is low or the result is too coarse
    coarse_types = {"country", "state", "county", "region"}
    uncertain = importance < 0.4 or result_type in coarse_types

    return GeoResult(
        latitude=cast(float, location.latitude),
        longitude=cast(float, location.longitude),
        display_name=str(location.address),
        uncertain=uncertain,
    )


def _matches_expected_location(
    raw: dict[str, Any], country_code: str | None, postal_code: str | None
) -> bool:
    address = raw.get("address")
    if not isinstance(address, dict):
        return country_code is None and postal_code is None

    if country_code:
        result_country = str(address.get("country_code", "")).casefold()
        if result_country != country_code.strip().casefold():
            return False

    if postal_code:
        result_postal_code = _normalise_postal_code(str(address.get("postcode", "")))
        if not result_postal_code or result_postal_code != _normalise_postal_code(postal_code):
            return False

    return True


def _normalise_postal_code(postal_code: str | None) -> str:
    return "".join(character for character in (postal_code or "").casefold() if character.isalnum())


def _legacy_result_matches(
    result: GeoResult, country_code: str | None, postal_code: str | None
) -> bool:
    display_name = result.display_name.casefold()
    if postal_code:
        compact_display_name = _normalise_postal_code(display_name)
        if _normalise_postal_code(postal_code) not in compact_display_name:
            return False

    if country_code:
        expected_names = _COUNTRY_DISPLAY_NAMES.get(country_code.strip().casefold())
        if expected_names is None or not any(name in display_name for name in expected_names):
            return False

    return True
