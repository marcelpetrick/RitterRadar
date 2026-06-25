# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Generic adapter for sites that list events in an HTML table."""

import logging
import re

from bs4 import BeautifulSoup

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.date_parser import parse_date_range
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

POSTAL_CODE_RE = re.compile(r"\b(\d{5})\b")
CITY_RE = re.compile(r"\b(\d{5})\s+([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+)*)")


@register("generic_table")
class GenericTableAdapter(AbstractCrawlerAdapter):
    """Fallback adapter: extracts rows from the first table on the page.

    Useful as a starting point for sites without a dedicated adapter.
    Column order heuristic: looks for date-like content to identify the
    date column, and uses remaining columns for name and location.
    """

    SOURCE_NAME = "Generic Table"
    BASE_URL = ""

    def __init__(self, url: str = "", source_name: str = "Generic Table") -> None:
        self.BASE_URL = url
        self.SOURCE_NAME = source_name

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        if not self.BASE_URL:
            return []
        try:
            response = await client.get(self.BASE_URL)
            response.raise_for_status()
        except Exception:
            logger.exception("GenericTableAdapter: failed to fetch %s", self.BASE_URL)
            return []

        soup = BeautifulSoup(response.text, "lxml")
        results: list[MarketData] = []

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows[1:]:  # skip header row
                cells = [td.get_text(separator=" ", strip=True) for td in row.find_all(["td", "th"])]
                if len(cells) < 2:
                    continue
                mdata = _parse_row(cells, self.BASE_URL)
                if mdata:
                    results.append(mdata)

        logger.info("GenericTableAdapter: found %d events at %s", len(results), self.BASE_URL)
        return results


def _parse_row(cells: list[str], source_url: str) -> MarketData | None:
    date_cell = name_cell = location_cell = None

    for i, cell in enumerate(cells):
        if parse_date_range(cell) is not None and date_cell is None:
            date_cell = cell
        elif name_cell is None and len(cell) > 3:
            name_cell = cell
        elif location_cell is None and len(cell) > 2:
            location_cell = cell

    if date_cell is None or name_cell is None:
        return None

    dates = parse_date_range(date_cell)
    if dates is None:
        return None

    start_date, end_date = dates
    postal_code = city = None
    if location_cell:
        m = CITY_RE.search(location_cell)
        if m:
            postal_code = m.group(1)
            city = m.group(2)
        elif (pm := POSTAL_CODE_RE.search(location_cell)):
            postal_code = pm.group(1)

    return MarketData(
        name=name_cell[:200],
        start_date=start_date,
        end_date=end_date,
        city=city,
        postal_code=postal_code,
        original_text=" | ".join(cells),
        source_url=source_url,
        confidence_score=0.6,
    )
