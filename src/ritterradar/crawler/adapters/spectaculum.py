# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for spectaculum.de (MPS — Mittelalterlich Phantasie Spectaculum).

Strategy: the /termine path returns 403, but the homepage lists all upcoming
events in the navigation as <a href="/termine/SLUG/">DATE CITY</a> links.
We parse those links and optionally follow each one for a postal code.
"""

__version__ = "0.1.0"
_VERIFIED_DATE = "2026-06-25"

import logging
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

BASE = "https://www.spectaculum.de"

# Matches nav link text like:
#   "25.07. + 26.07.2026Bückeburg 1"
#   "14.08. - 16.08.2026Weil am Rhein"
#   "06.05. - 09.05.2027Rastede"
_DATE_CITY_RE = re.compile(
    r"(\d{1,2})\.(\d{2})\."        # start day, start month
    r"\s*[+\-–]\s*"                 # separator (plus, hyphen, en-dash)
    r"(\d{1,2})\.(\d{2})\.(\d{4})" # end day, end month, year
    r"\s*(.*)",                      # city name (rest of string)
    re.S,
)

POSTAL_RE = re.compile(r"\b(\d{5})\b")


@register("spectaculum")
class SpectaculumAdapter(AbstractCrawlerAdapter):
    """Scraper for spectaculum.de event list from the homepage navigation."""

    SOURCE_NAME = "Spectaculum.de (MPS)"
    BASE_URL = BASE

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        results: list[MarketData] = []

        try:
            response = await client.get(BASE)
            response.raise_for_status()
        except Exception:
            logger.exception("%s: failed to fetch homepage %s", self.SOURCE_NAME, BASE)
            return []

        soup = BeautifulSoup(response.text, "lxml")

        # All event links in the nav have href like /termine/SLUG/
        event_links = [
            a for a in soup.find_all("a", href=True)
            if re.match(r"^/termine/\w", a["href"])
        ]

        seen: set[str] = set()
        for a in event_links:
            href: str = a["href"]
            if href in seen:
                continue
            seen.add(href)

            raw_text = a.get_text(separator=" ", strip=True)
            raw_text = " ".join(raw_text.split())  # collapse whitespace

            m = _DATE_CITY_RE.match(raw_text)
            if not m:
                logger.debug("%s: could not parse link text %r", self.SOURCE_NAME, raw_text)
                continue

            start_day, start_month, end_day, end_month, year_str, city_raw = m.groups()
            year = int(year_str)
            city = city_raw.strip()

            # Normalise city: strip trailing "1", "2" sub-event suffixes if purely numeric
            city_clean = re.sub(r"\s+\d+$", "", city).strip() or city

            try:
                start = date(year, int(start_month), int(start_day))
                end = date(year, int(end_month), int(end_day))
            except ValueError:
                logger.debug("%s: invalid date in %r", self.SOURCE_NAME, raw_text)
                continue

            source_url = urljoin(BASE, href)

            results.append(
                MarketData(
                    name=f"MPS {city_clean}",
                    start_date=start,
                    end_date=end,
                    city=city_clean,
                    source_url=source_url,
                    market_type="medieval",
                    confidence_score=0.95,
                    original_text=raw_text,
                )
            )

        logger.info("%s: scraped %d events", self.SOURCE_NAME, len(results))
        return results
