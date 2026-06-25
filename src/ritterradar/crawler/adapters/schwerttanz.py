# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for schwerttanz.de market calendar."""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.date_parser import parse_date_range
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

BASE = "https://schwerttanz.de"
POSTAL_RE = re.compile(r"\b(\d{5})\b")
CITY_RE = re.compile(r"\b(\d{5})\s+([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+)*)")


@register("schwerttanz")
class SchwerttanzAdapter(AbstractCrawlerAdapter):
    """Scraper for schwerttanz.de/marktkalender."""

    SOURCE_NAME = "Schwerttanz Marktkalender"
    BASE_URL = f"{BASE}/marktkalender"

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        results: list[MarketData] = []
        try:
            response = await client.get(self.BASE_URL)
            response.raise_for_status()
        except Exception:
            logger.exception("%s: failed to fetch %s", self.SOURCE_NAME, self.BASE_URL)
            return []

        soup = BeautifulSoup(response.text, "lxml")

        # schwerttanz tends to use tables or definition lists
        rows = soup.find_all("tr") or soup.find_all("dl") or soup.find_all("li")
        for row in rows:
            mdata = _parse_row(row)
            if mdata:
                results.append(mdata)

        logger.info("%s: scraped %d events", self.SOURCE_NAME, len(results))
        return results


def _parse_row(row: Tag) -> MarketData | None:
    full_text = row.get_text(separator=" ", strip=True)
    if len(full_text) < 10:
        return None

    dates = parse_date_range(full_text)
    if dates is None:
        return None
    start_date, end_date = dates

    # Title: first heading or bold text
    title_tag = row.find(["strong", "b", "h3", "h4", "td"])
    name = title_tag.get_text(strip=True) if title_tag else ""
    # Strip date from name if it leaked in
    if parse_date_range(name):
        name = ""
    if not name:
        # Fallback: take the longest non-date chunk
        chunks = [c.strip() for c in re.split(r"[\|,\n]", full_text) if c.strip()]
        non_date = [c for c in chunks if not parse_date_range(c) and len(c) > 5]
        name = non_date[0] if non_date else full_text[:60]

    city = postal_code = None
    m = CITY_RE.search(full_text)
    if m:
        postal_code = m.group(1)
        city = m.group(2)

    link = row.find("a", href=True)
    source_url = urljoin(BASE, link["href"]) if link else BASE  # type: ignore[index]

    return MarketData(
        name=name[:200],
        start_date=start_date,
        end_date=end_date,
        city=city,
        postal_code=postal_code,
        original_text=full_text[:1000],
        source_url=source_url,
        confidence_score=0.8,
    )
