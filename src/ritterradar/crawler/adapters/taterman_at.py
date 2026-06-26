# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for taterman.at — Austrian medieval-market iCal feed.

Fetches the "Markt" category iCal feed published by the taterman.at site
(wp-events-plugin.com v7.3.6 under WordPress).  No HTML scraping needed.

Feed URL:
    https://www.taterman.at/termin/categories/markt/?ical=1

Format: text/calendar  (RFC 5545 iCalendar)
Library: icalendar (PyPI)

VEVENT fields used:
    SUMMARY   → event name
    DTSTART   → start date (VALUE=DATE for all-day; datetime otherwise)
    DTEND     → exclusive end date for all-day events (subtract 1 day)
    URL       → canonical event page (used as source_url)
    LOCATION  → "Venue, [Street,] City, PLZ, Österreich"
    CATEGORIES → comma-separated tags incl. "Markt", province, theme

LOCATION parsing:
    Split by ", " → scan for a 4-digit PLZ; city = part immediately before PLZ.
    If that part is a known Austrian province name, city is left as None.
    Nominatim geocodes from PLZ alone in that case.

Market-type detection (SUMMARY keyword scan):
    Adventmarkt / Weihnacht  → christmas
    Wikinger / Viking        → viking
    Renaissance              → renaissance
    Fantasy                  → fantasy
    everything else          → medieval

Coverage: Austria exclusively (~26 events/year in 2026, growing).
Verified: 2026-06-26.
"""

import logging
import re
from datetime import date, timedelta

from icalendar import Calendar  # type: ignore[import-untyped]

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

__version__ = "0.1.0"
_VERIFIED_DATE = "2026-06-26"

_FEED_URL = "https://www.taterman.at/termin/categories/markt/?ical=1"
_PLZ_RE = re.compile(r"\b(\d{4})\b")

# Austrian province/state names that appear as "city" in LOCATION but are not cities.
# Wien and Salzburg are both province and city — keep them.
_PROVINCES = frozenset(
    {
        "Niederösterreich",
        "Oberösterreich",
        "NÖ",
        "OÖ",
        "Steiermark",
        "Tirol",
        "Vorarlberg",
        "Kärnten",
        "Burgenland",
    }
)

# Summary keyword → market_type (checked case-insensitively)
_TYPE_KEYWORDS: list[tuple[frozenset[str], str]] = [
    (frozenset({"adventmarkt", "weihnacht", "advent"}), "christmas"),
    (frozenset({"wikinger", "viking"}), "viking"),
    (frozenset({"renaissance"}), "renaissance"),
    (frozenset({"fantasy"}), "fantasy"),
]


def _detect_type(summary: str) -> str:
    lower = summary.lower()
    for keywords, mtype in _TYPE_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return mtype
    return "medieval"


def _parse_location(location: str) -> tuple[str | None, str | None]:
    """Return (city, postal_code) from a taterman LOCATION string."""
    if not location:
        return None, None
    parts = [p.strip() for p in location.split(",")]
    for i, part in enumerate(parts):
        m = _PLZ_RE.search(part)
        if m:
            plz = m.group(1)
            city: str | None = None
            if i > 0:
                candidate = parts[i - 1].strip()
                if candidate and candidate not in _PROVINCES:
                    city = candidate
            return city, plz
    # No PLZ found — try to extract city as second-to-last (before country)
    # Last part is usually "Österreich" or similar
    if len(parts) >= 2:
        candidate = parts[-2].strip()
        if candidate and candidate not in _PROVINCES and not _PLZ_RE.search(candidate):
            return candidate, None
    return None, None


def _coerce_date(dt_prop: object) -> date | None:
    """Convert icalendar DTSTART/DTEND value to a Python date.

    icalendar returns datetime.date for VALUE=DATE properties and
    datetime.datetime (possibly timezone-aware) for timed properties.
    datetime is a subclass of date, so we must check for datetime first.
    """
    val = dt_prop
    # datetime.datetime has a .date() method; datetime.date does not.
    date_method = getattr(val, "date", None)
    if callable(date_method):
        return date_method()  # type: ignore[return-value]
    if isinstance(val, date):
        return val  # type: ignore[return-value]
    return None


@register("taterman_at")
class TatermanAtAdapter(AbstractCrawlerAdapter):
    """Fetches Austrian medieval markets from taterman.at via iCal feed.

    The "Markt" category feed covers all years; only events from the current
    and next calendar year are returned.
    """

    SOURCE_NAME = "Taterman.at"
    BASE_URL = "https://www.taterman.at"

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        try:
            response = await client.get(_FEED_URL)
            response.raise_for_status()
        except Exception as exc:
            logger.error("%s: feed request failed: %s", self.SOURCE_NAME, exc)
            raise

        try:
            cal = Calendar.from_ical(response.content)
        except Exception as exc:
            logger.error("%s: iCal parse error: %s", self.SOURCE_NAME, exc)
            raise ValueError(f"iCal parse failed: {exc}") from exc

        today = date.today()
        min_year = today.year
        max_year = today.year + 1

        results: list[MarketData] = []

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            dtstart_prop = component.get("DTSTART")
            dtend_prop = component.get("DTEND")
            if dtstart_prop is None:
                continue

            raw_start = dtstart_prop.dt
            raw_end = dtend_prop.dt if dtend_prop is not None else None

            # taterman uses the non-standard DTSTART;TZID=...;VALUE=DATE combo,
            # causing icalendar to return timezone-aware datetime instead of date.
            # Detect all-day via the VALUE=DATE property parameter directly.
            all_day = dtstart_prop.params.get("VALUE") == "DATE"
            start = _coerce_date(raw_start)
            if start is None:
                continue

            if all_day and raw_end is not None:
                # RFC 5545: DTEND for all-day events is exclusive (day after last day)
                end = _coerce_date(raw_end)
                if end is not None and end > start:
                    end = end - timedelta(days=1)
            else:
                end = _coerce_date(raw_end)
            if end is None:
                end = start

            if not (min_year <= start.year <= max_year):
                continue

            name = str(component.get("SUMMARY", "")).strip()
            if not name:
                continue

            url = str(component.get("URL", "") or "").strip() or self.BASE_URL
            location = str(component.get("LOCATION", "") or "").strip()
            city, postal_code = _parse_location(location)
            market_type = _detect_type(name)

            results.append(
                MarketData(
                    name=name[:200],
                    start_date=start,
                    end_date=end,
                    city=city,
                    postal_code=postal_code,
                    country="AT",
                    market_type=market_type,
                    source_url=url,
                    confidence_score=0.9,
                    original_text=f"{name} {location}".strip()[:500],
                )
            )

        logger.info(
            "%s: %d events parsed from iCal feed (years %d–%d)",
            self.SOURCE_NAME,
            len(results),
            min_year,
            max_year,
        )
        return results
