# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for mittelalterkalender.info — largest German medieval event calendar.

Page structure (verified 2026-06-25):
  URL: /mittelaltermarkt/mittelalterfeste-{YEAR}-nach-datum.php
  Each event is a <tr class="isbfilter"> with 6 cells:
    [0] start date text + " bis " span  → strip to "DD.MM.YYYY"
    [1] end date "DD.MM.YYYY"
    [2] <button formaction="URL">Event name</button>
    [3] PLZ (5-digit postal code)
    [4] City name
    [5] Details button (same URL as [2])
"""

__version__ = "0.1.0"
_VERIFIED_DATE = "2026-06-25"

import logging
import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

BASE = "https://www.mittelalterkalender.info"
_DATE_FMT = "%d.%m.%Y"
_DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")
# Detect type from event title
_TYPE_KEYWORDS: dict[str, list[str]] = {
    "christmas":   ["weihnacht", "advent", "nikolaus", "winter"],
    "viking":      ["wikinger", "viking", "nordisch", "haithabu"],
    "renaissance": ["renaissance", "historisch", "landsknecht"],
    "fantasy":     ["fantasy", "drachen", "magie", "elfen", "mytho"],
}


def _list_url(year: int) -> str:
    return f"{BASE}/mittelaltermarkt/mittelalterfeste-{year}-nach-datum.php"


def _parse_date(text: str) -> date | None:
    # Cell text is "DD.MM.YYYYbis" or "DD.MM.YYYY" — extract with regex
    m = _DATE_RE.search(text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(0), _DATE_FMT).date()
    except ValueError:
        return None


def _detect_type(text: str) -> str:
    low = text.lower()
    for mtype, keywords in _TYPE_KEYWORDS.items():
        if any(k in low for k in keywords):
            return mtype
    return "medieval"


def _parse_row(row: Tag) -> MarketData | None:
    cells = row.find_all("td")
    if len(cells) < 5:
        return None

    start = _parse_date(cells[0].get_text(strip=True))
    end   = _parse_date(cells[1].get_text(strip=True))
    if start is None or end is None:
        return None

    # Event name lives inside the button element
    btn = cells[2].find("button")
    name = btn.get_text(strip=True) if btn else cells[2].get_text(strip=True)
    if not name:
        return None

    postal_code = cells[3].get_text(strip=True) or None
    city        = cells[4].get_text(strip=True) or None

    # Detail page URL from button formaction attribute
    source_url = BASE
    if btn and btn.get("formaction"):
        source_url = urljoin(BASE, btn["formaction"])

    return MarketData(
        name=name[:200],
        start_date=start,
        end_date=end,
        city=city,
        postal_code=postal_code,
        source_url=source_url,
        market_type=_detect_type(name),
        confidence_score=0.9,
        original_text=row.get_text(separator=" ", strip=True)[:500],
    )


@register("mittelalterkalender_info")
class MittelalterkalenderInfoAdapter(AbstractCrawlerAdapter):
    """Scraper for mittelalterkalender.info — 800+ events per year."""

    SOURCE_NAME = "Mittelalterkalender.info"
    BASE_URL = BASE

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        results: list[MarketData] = []
        today = date.today()

        for year in (today.year, today.year + 1):
            url = _list_url(year)
            try:
                response = await client.get(url)
                response.raise_for_status()
            except Exception:
                logger.warning("%s: failed to fetch %s", self.SOURCE_NAME, url)
                continue

            soup = BeautifulSoup(response.text, "lxml")
            rows = soup.find_all("tr", class_="isbfilter")
            logger.info("%s: %d rows found for %d", self.SOURCE_NAME, len(rows), year)

            for row in rows:
                mdata = _parse_row(row)
                if mdata:
                    results.append(mdata)

        logger.info("%s: scraped %d events total", self.SOURCE_NAME, len(results))
        return results
