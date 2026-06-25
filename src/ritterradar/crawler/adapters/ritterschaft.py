# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for ritterschaft.de event listings."""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.date_parser import parse_date_range
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

BASE = "https://www.ritterschaft.de"
POSTAL_RE = re.compile(r"\b(\d{5})\b")
CITY_RE = re.compile(r"\b(\d{5})\s+([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+)*)")


@register("ritterschaft")
class RitterschaftAdapter(AbstractCrawlerAdapter):
    """Scraper for ritterschaft.de/termine."""

    SOURCE_NAME = "Ritterschaft.de"
    BASE_URL = f"{BASE}/termine"

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        results: list[MarketData] = []
        try:
            response = await client.get(self.BASE_URL)
            response.raise_for_status()
        except Exception:
            logger.exception("%s: failed to fetch %s", self.SOURCE_NAME, self.BASE_URL)
            return []

        soup = BeautifulSoup(response.text, "lxml")
        items = soup.find_all(class_=re.compile(r"event|termin|veranstaltung|markt|eintrag", re.I))
        if not items:
            items = soup.find_all("article") or soup.find_all("li")

        for item in items:
            mdata = _parse_item(item)
            if mdata:
                results.append(mdata)

        logger.info("%s: scraped %d events", self.SOURCE_NAME, len(results))
        return results


def _parse_item(item: Tag) -> MarketData | None:
    full_text = item.get_text(separator=" ", strip=True)
    if len(full_text) < 10:
        return None

    dates = parse_date_range(full_text)
    if dates is None:
        return None
    start_date, end_date = dates

    heading = item.find(["h2", "h3", "h4", "strong"])
    name = heading.get_text(strip=True) if heading else ""
    if not name or parse_date_range(name):
        chunks = [c.strip() for c in full_text.split() if len(c.strip()) > 3]
        name = " ".join(chunks[:8])

    city = postal_code = None
    m = CITY_RE.search(full_text)
    if m:
        postal_code = m.group(1)
        city = m.group(2)

    link = item.find("a", href=True)
    source_url = urljoin(BASE, link["href"]) if link else BASE  # type: ignore[index]

    return MarketData(
        name=name[:200],
        start_date=start_date,
        end_date=end_date,
        market_type="medieval",
        city=city,
        postal_code=postal_code,
        original_text=full_text[:1000],
        source_url=source_url,
        confidence_score=0.8,
    )
