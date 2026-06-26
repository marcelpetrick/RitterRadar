# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for marktkalendarium.de (Pfalzis Marktkalendarium).

Page structure (verified 2026-06-25):
  URL: https://marktkalendarium.de/maerkte{YEAR}.php
  334 rows for 2026, 301 of which are in Germany.

  Each event row has 7 <td> cells:
    [0] start date  "D.M.YYYY" or "DD.M.YYYY" or "DD.MM.YYYY"
    [1] end date    same format
    [2] event name  plain text
    [3] location    <a href="https://maps.google.de/maps?q=D-XXXXX City">D-XXXXX City</a>
                    prefix: D- (DE), A- (AT), CH- (CH), L- (LU), ...
    [4] venue       plain text (e.g. "Innenstadt", "Schlossgarten")
    [5] website     <a href="URL">Name</a>  — primary source URL
    [6] contact     optional second link or email

Country prefixes seen in 2026 data:
  D- → DE (301 events)
  A- → AT (9 events)
  CH / Ch → CH (11 events)
  L- → LU (4 events)
  DK → DK (2 events)
  I- → IT (2 events)
  B- → BE (1 event)
  NL → NL (1 event)
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
_VERIFIED_DATE = "2026-06-25"

BASE = "https://marktkalendarium.de"

# Date cells use variable-width parts: "6.6.2026" or "26.12.2026"
_DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")

# Country-code prefix → ISO 3166-1 alpha-2
_COUNTRY_MAP: dict[str, str] = {
    "D-": "DE",
    "A-": "AT",
    "CH-": "CH",
    "CH": "CH",
    "Ch-": "CH",
    "Ch": "CH",
    "L-": "LU",
    "DK": "DK",
    "I-": "IT",
    "B-": "BE",
    "NL": "NL",
    "NL-": "NL",
}

# Detect special market types from name
_TYPE_KEYWORDS: dict[str, list[str]] = {
    "christmas": ["weihnacht", "advent", "nikolaus", "winter", "christkind"],
    "viking": ["wikinger", "viking", "nordisch", "haithabu", "keltisch", "celtic", "kelt"],
    "renaissance": ["renaissance", "historisch", "landsknecht", "baroque"],
    "fantasy": ["fantasy", "drachen", "magie", "elfen", "mytho", "steampunk", "pirat"],
}


def _parse_date(text: str) -> date | None:
    m = _DATE_RE.search(text.strip())
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _parse_location(cell: Tag) -> tuple[str | None, str | None, str]:
    """Return (postal_code, city, country_iso) from the location cell."""
    raw = cell.get_text(strip=True)
    # raw example: "D-55232 Alzey" or "A-1010 Wien" or "CH-8001 Zürich"
    country = "DE"
    for prefix, iso in _COUNTRY_MAP.items():
        if raw.upper().startswith(prefix.upper()):
            country = iso
            raw = raw[len(prefix) :]
            break

    parts = raw.strip().split(None, 1)  # split on first whitespace
    postal_code = parts[0] if parts else None
    city = parts[1] if len(parts) > 1 else None

    # Validate postal code: must be at least 4 digits
    if postal_code and not re.match(r"^\d{4,6}$", postal_code):
        postal_code = None

    return postal_code, city, country


def _extract_source_url(cell: Tag) -> str:
    """Pick the first external (non-Google, non-mailto) link from the website cell."""
    for a in cell.find_all("a", href=True):
        href: str = a["href"]
        if href.startswith("http") and "maps.google" not in href:
            return href
    return BASE


def _detect_type(name: str) -> str:
    low = name.lower()
    for mtype, keywords in _TYPE_KEYWORDS.items():
        if any(k in low for k in keywords):
            return mtype
    return "medieval"


def _parse_row(row: Tag) -> MarketData | None:
    cells = row.find_all("td")
    if len(cells) < 6:
        return None

    start = _parse_date(cells[0].get_text(strip=True))
    end = _parse_date(cells[1].get_text(strip=True))
    if start is None:
        return None
    if end is None:
        end = start  # single-day event (shouldn't occur but defensive)

    name = cells[2].get_text(strip=True)
    if not name:
        return None

    postal_code, city, country = _parse_location(cells[3])
    source_url = _extract_source_url(cells[5])

    return MarketData(
        name=name[:200],
        start_date=start,
        end_date=end,
        city=city,
        postal_code=postal_code,
        country=country,
        source_url=source_url,
        market_type=_detect_type(name),
        confidence_score=0.85,
        original_text=row.get_text(separator=" ", strip=True)[:500],
    )


@register("marktkalendarium")
class MarktkalendariumAdapter(AbstractCrawlerAdapter):
    """Scraper for Pfalzis Marktkalendarium — 300+ German events per year."""

    SOURCE_NAME = "Pfalzis Marktkalendarium"
    BASE_URL = BASE

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        results: list[MarketData] = []
        today = date.today()

        for year in (today.year, today.year + 1):
            url = f"{BASE}/maerkte{year}.php"
            try:
                response = await client.get(url)
                response.raise_for_status()
            except Exception:
                logger.warning("%s: failed to fetch %s", self.SOURCE_NAME, url)
                continue

            soup = BeautifulSoup(response.text, "lxml")

            # All rows containing dates — no class selector needed
            date_rows = [
                tr
                for tr in soup.find_all("tr")
                if _DATE_RE.search(tr.get_text()) and len(tr.find_all("td")) >= 6
            ]
            logger.info("%s: %d rows found for %d", self.SOURCE_NAME, len(date_rows), year)

            for row in date_rows:
                mdata = _parse_row(row)
                if mdata:
                    results.append(mdata)

        logger.info("%s: scraped %d events total", self.SOURCE_NAME, len(results))
        return results
