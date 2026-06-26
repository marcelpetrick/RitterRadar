# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for trollfelsen.de — vendor tour-date schedule.

Trollfelsen is a medieval-market trader; this page lists the events they
attend.  The dataset is small (~21 confirmed events in 2026) but each card
links directly to the event's own website, providing high-quality source
URLs.

Page URL: https://trollfelsen.de/termine

Card structure (class="event-card"):
    <div class="picture"><a href="EVENT_URL">...</a></div>
    <div class="infos">
      <h3>Event name</h3>
      <div>
        <div class="font-weight-bold">DD.MM.YYYY - DD.MM.YYYY</div>
        ...
      </div>
      <div>Mehr von: Organizer name</div>
      <div class="icons">social links</div>
      <div>Venue</div>
      <div>Street</div>
      <div>COUNTRY - PLZ  City</div>   ← e.g. "DE - 06217 Merseburg"
      <div>* Teilnahme noch nicht bestätigt</div>   ← unconfirmed flag
    </div>

Filtering: cards containing "nicht bestätigt" (not confirmed) are skipped.

Date parsing:
    "DD.MM.YYYY - DD.MM.YYYY"  →  start_date / end_date

Location parsing:
    "DE - 06217 Merseburg"  →  country=DE, postal_code="06217", city="Merseburg"

Coverage: Germany (primarily), Austria, Switzerland.
Verified: 2026-06-26.
"""

import logging
import re
from datetime import date

from bs4 import BeautifulSoup, Tag

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

__version__ = "0.1.0"
_VERIFIED_DATE = "2026-06-26"

_URL = "https://trollfelsen.de/termine"

_DATE_RANGE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s*[-–]\s*(\d{2})\.(\d{2})\.(\d{4})")
_LOCATION_RE = re.compile(r"^([A-Z]{2})\s*[-–]\s*(\d{4,5})\s+(.+)$", re.MULTILINE)

# Country abbreviation → ISO 3166-1 alpha-2 (trollfelsen uses its own 2-letter codes)
_COUNTRY_MAP = {"DE": "DE", "AT": "AT", "CH": "CH", "LU": "LU", "NL": "NL"}


def _parse_date_range(text: str) -> tuple[date, date] | None:
    m = _DATE_RANGE_RE.search(text)
    if not m:
        return None
    sd, sm, sy, ed, em, ey = m.groups()
    try:
        start = date(int(sy), int(sm), int(sd))
        end = date(int(ey), int(em), int(ed))
        return start, end
    except ValueError:
        return None


def _parse_location(text: str) -> tuple[str | None, str | None, str]:
    """Extract (postal_code, city, country_iso) from a location string."""
    m = _LOCATION_RE.search(text)
    if m:
        country_code = m.group(1)
        postal_code = m.group(2)
        city = m.group(3).strip()
        # city may have trailing notes after the actual city name
        city = re.split(r"[\|,;]", city)[0].strip()
        country = _COUNTRY_MAP.get(country_code, country_code)
        return postal_code, city or None, country
    return None, None, "DE"


def _parse_card(card: Tag) -> MarketData | None:
    text = card.get_text(separator="\n", strip=True)

    # Skip unconfirmed appearances
    if "nicht bestätigt" in text.lower():
        return None

    # Event name from h3
    h3 = card.find("h3")
    name = h3.get_text(strip=True) if h3 else ""
    if not name:
        return None

    # Date range
    dates = _parse_date_range(text)
    if dates is None:
        return None
    start_date, end_date = dates

    # Source URL: first external link in .picture div
    picture = card.find(class_="picture")
    source_url = _URL
    if picture:
        link = picture.find("a", href=True)
        if link and link["href"].startswith("http"):
            source_url = link["href"]

    # Location
    postal_code, city, country = _parse_location(text)

    return MarketData(
        name=name[:200],
        start_date=start_date,
        end_date=end_date,
        city=city,
        postal_code=postal_code,
        country=country,
        market_type="medieval",
        source_url=source_url,
        confidence_score=0.9,
        original_text=text[:500],
    )


@register("trollfelsen")
class TrollfelsensAdapter(AbstractCrawlerAdapter):
    """Scraper for trollfelsen.de vendor tour schedule.

    Yields only confirmed appearances (skips cards marked "nicht bestätigt").
    Each card's event-website link is used as source_url where available.
    """

    SOURCE_NAME = "Trollfelsen.de"
    BASE_URL = _URL

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        try:
            response = await client.get(_URL)
            response.raise_for_status()
        except Exception as exc:
            logger.error("%s: page request failed: %s", self.SOURCE_NAME, exc)
            raise

        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.find_all(class_="event-card")
        logger.info("%s: found %d event cards", self.SOURCE_NAME, len(cards))

        results: list[MarketData] = []
        today = date.today()
        for card in cards:
            mdata = _parse_card(card)
            if mdata and mdata.start_date.year >= today.year:
                results.append(mdata)

        logger.info(
            "%s: %d confirmed events for %d+",
            self.SOURCE_NAME,
            len(results),
            today.year,
        )
        return results
