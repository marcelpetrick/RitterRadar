# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for mittelaltermarkt.com — German medieval market directory."""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.date_parser import parse_date_range
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

BASE = "https://www.mittelaltermarkt.com"
POSTAL_RE = re.compile(r"\b(\d{5})\b")
CITY_RE = re.compile(r"\b(\d{5})\s+([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+)*)")


@register("mittelaltermarkt")
class MittelaltermarktAdapter(AbstractCrawlerAdapter):
    """Scraper for mittelaltermarkt.com event listings."""

    SOURCE_NAME = "Mittelaltermarkt.com"
    BASE_URL = f"{BASE}/marktkalender"

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        results: list[MarketData] = []

        for page in range(1, 5):
            url = self.BASE_URL if page == 1 else f"{self.BASE_URL}/page/{page}"
            try:
                response = await client.get(url)
                if response.status_code in (404, 410):
                    break
                response.raise_for_status()
            except Exception:
                logger.exception("%s: failed to fetch page %d", self.SOURCE_NAME, page)
                break

            soup = BeautifulSoup(response.text, "lxml")

            # Try progressively wider selectors
            items = (
                soup.find_all(
                    class_=re.compile(r"event|markt|eintrag|post|veranstaltung|termin|entry", re.I)
                )
                or soup.find_all("article")
                or soup.find_all("tr")[1:]  # table-based calendars
                or soup.find_all("li", class_=True)
            )

            if not items and page == 1:
                title = soup.title.get_text(strip=True) if soup.title else "(no title)"
                snippet = soup.get_text(separator=" ", strip=True)[:500]
                logger.debug(
                    "%s: no items found on page 1. title=%r snippet=%r",
                    self.SOURCE_NAME,
                    title,
                    snippet,
                )

            page_count = 0
            for item in items:
                mdata = _parse_item(item)
                if mdata:
                    results.append(mdata)
                    page_count += 1

            if page_count == 0:
                break

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

    heading = item.find(["h1", "h2", "h3", "h4"])
    name = heading.get_text(strip=True) if heading else ""
    if not name:
        return None

    city = postal_code = None
    m = CITY_RE.search(full_text)
    if m:
        postal_code = m.group(1)
        city = m.group(2)

    link = item.find("a", href=True)
    source_url = urljoin(BASE, link["href"]) if link else BASE  # type: ignore[index]

    market_type = _detect_type(name + " " + full_text)

    return MarketData(
        name=name[:200],
        start_date=start_date,
        end_date=end_date,
        market_type=market_type,
        city=city,
        postal_code=postal_code,
        original_text=full_text[:1000],
        source_url=source_url,
        confidence_score=0.85,
    )


def _detect_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("renaissance", "historisch")):
        return "renaissance"
    if any(w in t for w in ("wikinger", "viking", "nordisch")):
        return "viking"
    if any(w in t for w in ("weihnacht", "advent")):
        return "christmas"
    if any(w in t for w in ("fantasy", "drachen", "magie")):
        return "fantasy"
    return "medieval"
