# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for mittelaltermarkt.online — WordPress site using The Events Calendar plugin.

Uses the REST API at /wp-json/tribe/events/v1/events (no scraping needed).
Verified 2026-06-25.

API endpoint: GET /wp-json/tribe/events/v1/events
Query params:
  per_page    — number of events per page (max 100)
  status      — "publish"
  start_date  — ISO date filter
  end_date    — ISO date filter
  page        — 1-based page number

Response:
  {
    "events":      [...],
    "total":       531,
    "total_pages": 11,
    "next_rest_url": "https://..."
  }

Event object (relevant fields):
  title        — event name
  start_date   — "YYYY-MM-DD HH:MM:SS"
  end_date     — "YYYY-MM-DD HH:MM:SS"
  url          — canonical event page URL (used as source_url)
  website      — optional external organiser website
  categories   — [{slug: "mittelalterspektakel", ...}, ...]
  venue        — {city, zip, country, geo_lat, geo_lng, ...}

Venue coordinates (geo_lat / geo_lng) are present in ~98% of events;
when available they are passed directly in MarketData.latitude/longitude
to skip Nominatim geocoding.

Category-to-market-type mapping:
  mittelaltermaerkten        → medieval
  mittelalterspektakel       → medieval
  mittelalterfeste           → medieval
  andere-veranstaltungen     → medieval
  ritterturniere             → medieval
  historische-feste          → medieval
  weihnachtsmaerkte          → christmas
  wikingerspektakel          → viking
  renaissance-*              → renaissance
  fantasy-*                  → fantasy
"""

__version__ = "0.1.0"
_VERIFIED_DATE = "2026-06-25"

import html
import logging
from datetime import date, datetime

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

BASE = "https://mittelaltermarkt.online"
_API_URL = f"{BASE}/wp-json/tribe/events/v1/events"
_PER_PAGE = 100
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

# German country names accepted as "DE"
_GERMAN_NAMES = {"deutschland", "germany"}

# Category slug → market_type
_CATEGORY_TYPE: dict[str, str] = {
    "weihnachtsmaerkte":     "christmas",
    "wikingerspektakel":     "viking",
    "wikinger":              "viking",
    "renaissance":           "renaissance",
    "renaissance-feste":     "renaissance",
    "fantasyfeste":          "fantasy",
    "fantasy-feste":         "fantasy",
}
_MEDIEVAL_SLUGS = {
    "mittelaltermaerkten",
    "mittelalterspektakel",
    "mittelalterfeste",
    "ritterturniere",
    "historische-feste",
    "andere-veranstaltungen",
}

# Country display name → ISO 3166-1 alpha-2
_COUNTRY_ISO: dict[str, str] = {
    "Deutschland": "DE",
    "Germany":     "DE",
    "Österreich":  "AT",
    "Austria":     "AT",
    "Schweiz":     "CH",
    "Switzerland": "CH",
    "Luxemburg":   "LU",
    "Luxembourg":  "LU",
}


def _parse_date(raw: str) -> date | None:
    try:
        return datetime.strptime(raw, _DATE_FMT).date()
    except (ValueError, TypeError):
        return None


def _detect_type(categories: list[dict]) -> str:
    for cat in categories:
        slug: str = cat.get("slug", "")
        if slug in _CATEGORY_TYPE:
            return _CATEGORY_TYPE[slug]
        for prefix in ("weihnacht", "advent"):
            if slug.startswith(prefix):
                return "christmas"
        for prefix in ("wikinger", "viking"):
            if slug.startswith(prefix):
                return "viking"
        for prefix in ("fantasy",):
            if slug.startswith(prefix):
                return "fantasy"
        for prefix in ("renaissance",):
            if slug.startswith(prefix):
                return "renaissance"
    return "medieval"


def _parse_event(ev: dict) -> MarketData | None:
    name: str = html.unescape(ev.get("title", "")).strip()
    if not name:
        return None

    start = _parse_date(ev.get("start_date", ""))
    end   = _parse_date(ev.get("end_date", ""))
    if start is None:
        return None
    if end is None:
        end = start

    source_url: str = ev.get("url", BASE)

    # Venue data
    venue: dict = ev.get("venue") or {}
    city         = venue.get("city") or None
    postal_code  = venue.get("zip") or None
    country_raw  = venue.get("country", "Deutschland")
    country      = _COUNTRY_ISO.get(country_raw, "DE")
    geo_lat: float | None = venue.get("geo_lat") or None
    geo_lng: float | None = venue.get("geo_lng") or None

    # Postal code cleanup (some entries have spaces or letters)
    if postal_code:
        postal_code = postal_code.strip()
        if not any(c.isdigit() for c in postal_code):
            postal_code = None

    categories: list[dict] = ev.get("categories") or []
    market_type = _detect_type(categories)

    return MarketData(
        name=name[:200],
        start_date=start,
        end_date=end,
        city=city,
        postal_code=postal_code,
        country=country,
        source_url=source_url,
        market_type=market_type,
        confidence_score=0.9,
        original_text=f"{name} {city or ''} {postal_code or ''}".strip()[:500],
        latitude=geo_lat,
        longitude=geo_lng,
    )


@register("mittelaltermarkt_online")
class MittelaltermarktOnlineAdapter(AbstractCrawlerAdapter):
    """Scraper for mittelaltermarkt.online via The Events Calendar REST API.

    No HTML scraping — uses structured JSON API. Pre-geocoded coordinates
    from venue.geo_lat / venue.geo_lng are passed through to skip Nominatim.
    """

    SOURCE_NAME = "Mittelaltermarkt.online"
    BASE_URL = BASE

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        results: list[MarketData] = []
        today = date.today()
        start_filter = f"{today.year}-01-01"
        end_filter   = f"{today.year + 1}-12-31"

        page = 1
        total_pages = 1  # updated after first response

        while page <= total_pages:
            params = (
                f"per_page={_PER_PAGE}&status=publish"
                f"&start_date={start_filter}&end_date={end_filter}&page={page}"
            )
            url = f"{_API_URL}?{params}"
            try:
                response = await client.get(url)
                response.raise_for_status()
            except Exception:
                logger.warning("%s: failed to fetch page %d", self.SOURCE_NAME, page)
                break

            try:
                data: dict = response.json()
            except Exception:
                logger.warning("%s: non-JSON response on page %d", self.SOURCE_NAME, page)
                break

            if page == 1:
                total_pages = int(data.get("total_pages", 1))
                total = int(data.get("total", 0))
                logger.info(
                    "%s: %d events across %d pages",
                    self.SOURCE_NAME, total, total_pages,
                )

            events: list[dict] = data.get("events") or []
            for ev in events:
                mdata = _parse_event(ev)
                if mdata:
                    results.append(mdata)

            page += 1

        pre_geocoded = sum(1 for r in results if r.latitude is not None)
        logger.info(
            "%s: scraped %d events (%d with pre-geocoded coords, %d need Nominatim)",
            self.SOURCE_NAME, len(results), pre_geocoded, len(results) - pre_geocoded,
        )
        return results
