# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for mittelalterfeste.de — large German medieval event calendar."""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.date_parser import parse_date_range
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

BASE = "https://www.mittelalterfeste.de"
POSTAL_RE = re.compile(r"\b(\d{5})\b")
CITY_RE = re.compile(r"\b(\d{5})\s+([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+)*)")


@register("mittelalterfeste")
class MittelalterfestAdapter(AbstractCrawlerAdapter):
    """Scraper for mittelalterfeste.de event listings.

    The site lists events in article/div cards.  Selectors target the
    common "event-item" / "veranstaltung" patterns observed on German
    event calendar sites — adjust if the site structure changes.
    """

    SOURCE_NAME = "Mittelalterfeste.de"
    BASE_URL = f"{BASE}/termine"

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        results: list[MarketData] = []
        url = self.BASE_URL

        for page in range(1, 6):
            page_url = url if page == 1 else f"{url}?seite={page}"
            try:
                response = await client.get(page_url)
                if response.status_code == 404:
                    break
                response.raise_for_status()
            except Exception:
                logger.exception("%s: failed to fetch page %d", self.SOURCE_NAME, page)
                break

            soup = BeautifulSoup(response.text, "lxml")
            items = (
                soup.find_all("article", class_=re.compile(r"event|veranstaltung|markt", re.I))
                or soup.find_all("div", class_=re.compile(r"event|veranstaltung|markt|item", re.I))
                or soup.find_all("li", class_=re.compile(r"event|veranstaltung", re.I))
            )

            if not items:
                # Fallback: look for any card-like divs with a heading + date text
                items = soup.find_all("div", class_=re.compile(r"card|entry|post", re.I))

            found_on_page = 0
            for item in items:
                mdata = _parse_item(item, self.SOURCE_NAME)
                if mdata:
                    results.append(mdata)
                    found_on_page += 1

            if found_on_page == 0:
                break  # no more pages

        logger.info("%s: scraped %d events", self.SOURCE_NAME, len(results))
        return results


def _parse_item(item: Tag, source_name: str) -> MarketData | None:
    # Title
    title_tag = item.find(["h1", "h2", "h3", "h4", "strong"])
    if not title_tag:
        return None
    name = title_tag.get_text(strip=True)
    if not name or len(name) < 3:
        return None

    full_text = item.get_text(separator=" ", strip=True)

    # Date — scan all text nodes for a parseable date
    dates = None
    for element in item.find_all(string=True):
        candidate = element.strip()
        if not candidate:
            continue
        parsed = parse_date_range(candidate)
        if parsed:
            dates = parsed
            break

    if dates is None:
        dates = parse_date_range(full_text)
    if dates is None:
        return None

    start_date, end_date = dates

    # Location
    city = postal_code = None
    location_tag = item.find(class_=re.compile(r"location|ort|city|adresse", re.I))
    location_text = location_tag.get_text(strip=True) if location_tag else full_text

    m = CITY_RE.search(location_text)
    if m:
        postal_code = m.group(1)
        city = m.group(2)
    elif (pm := POSTAL_RE.search(location_text)):
        postal_code = pm.group(1)

    # Source URL
    link = item.find("a", href=True)
    source_url = urljoin(BASE, link["href"]) if link else BASE  # type: ignore[index]

    # Market type
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
        source_name=source_name,
        confidence_score=0.85,
    )


def _detect_type(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ("renaissance", "historisch")):
        return "renaissance"
    if any(w in text_lower for w in ("wikinger", "viking", "nordisch")):
        return "viking"
    if any(w in text_lower for w in ("weihnacht", "advent", "christmas")):
        return "christmas"
    if any(w in text_lower for w in ("fantasy", "magie", "mystik", "drachen")):
        return "fantasy"
    return "medieval"
