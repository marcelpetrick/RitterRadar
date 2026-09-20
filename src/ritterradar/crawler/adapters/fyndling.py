# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for fyndling.de — European medieval and Viking market directory.

Fyndling lists ~2,700 markets for the current year in one server-rendered
table; ~1,300 of them are in Germany, Austria, Switzerland, Liechtenstein and
Luxembourg. robots.txt allows crawling (only /admin/ is disallowed).

Page URL: https://fyndling.de/maerkte.html

Row structure:
    <tr data-date="2026-01-02" id="9e0b278e7ed68c06">
      <td>02.01.2026 - 04.01.2026</td>          ← or a single "04.01.2026"
      <td><a href="https://fyndling.de/e/9e0b278e7ed68c06">Name</a></td>
      <td>63785 Obernburg am Main</td>          ← German rows: no country suffix
    </tr>
    Foreign rows end with a flag and ISO code: "21700 Nuits-Saint-Georges (🇫🇷FR)".
    Month/week heading rows have no data-date attribute and are ignored.

Filtering: only DACH + LI + LU rows with a postal code or city are kept, so
the crawler does not spend Nominatim requests on events outside the map's
focus. The page only covers the current year.

Verified: 2026-09-13.
"""

import logging
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

__version__ = "0.3.0"
_VERIFIED_DATE = "2026-09-19"

_URL = "https://fyndling.de/maerkte.html"

_DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
# "(🇫🇷FR)" — optional regional-indicator flag followed by an ISO country code
_COUNTRY_RE = re.compile(r"\(\s*[\U0001F1E6-\U0001F1FF]*\s*([A-Z]{2})\s*\)\s*$")
_POSTAL_CITY_RE = re.compile(r"^(?:[A-Z]{1,2}[-.])?(\d{4,5})(?:\s+(.+))?$")
_CITY_POSTAL_RE = re.compile(r"^(.+?)\s+(\d{4,5})$")  # "Drage 21423"
# Older entries mark the country after the city: "39040 Campo di Trens (I)"
_LEGACY_MARKER_RE = re.compile(r"\s*\((A|D|F|I|L)\)\s*$")
_LEGACY_COUNTRY = {"A": "AT", "D": "DE", "F": "FR", "I": "IT", "L": "LU"}
_SWISS_CANTONS = frozenset(
    {
        "AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR", "JU", "LU", "NE",
        "NW", "OW", "SG", "SH", "SO", "SZ", "TG", "TI", "UR", "VD", "VS", "ZG", "ZH",
    }
)  # fmt: skip
_COUNTRIES = frozenset({"DE", "AT", "CH", "LI", "LU"})
_TYPE_KEYWORDS: dict[str, list[str]] = {
    "christmas": ["weihnacht", "advent", "rauhnacht", "raunacht"],
    "viking": ["wikinger", "viking"],
    "renaissance": ["renaissance"],
    "fantasy": ["fantasy"],
}


def _parse_dates(text: str) -> tuple[date, date] | None:
    found = _DATE_RE.findall(text)
    if not found:
        return None
    try:
        dates = [date(int(y), int(m), int(d)) for d, m, y in found[:2]]
    except ValueError:
        return None
    start, end = dates[0], dates[-1]
    return start, max(start, end)


def _clean_city(city: str, country: str) -> str | None:
    city = re.sub(r"\s*\(wo immer .*?\)", "", city, flags=re.I).strip()
    if city.casefold() == "neues ok" or re.fullmatch(r"\d*x+", city, re.I):
        return None
    words = city.split()
    # Swiss places often carry their canton: "Zofingen AG", "Laupen BE"
    if country == "CH" and len(words) > 1 and words[-1] in _SWISS_CANTONS:
        words = words[:-1]
    # Venue and municipality are sometimes repeated: "Schloss Lenzburg Lenzburg AG".
    if len(words) >= 3 and words[-1].casefold() == words[-2].casefold():
        words = [words[-1]]
    return " ".join(words) or None


def _parse_location(text: str) -> tuple[str | None, str | None, str]:
    """Return (postal_code, city, country) for a location cell."""
    m = _COUNTRY_RE.search(text)
    country = m.group(1) if m else "DE"
    body = _COUNTRY_RE.sub("", text).strip()
    legacy = _LEGACY_MARKER_RE.search(body)
    if legacy:
        if m is None:
            country = _LEGACY_COUNTRY[legacy.group(1)]
        body = body[: legacy.start()].strip()

    pm = _POSTAL_CITY_RE.match(body)
    if pm:
        return pm.group(1), _clean_city(pm.group(2) or "", country), country
    cm = _CITY_POSTAL_RE.match(body)
    if cm:
        return cm.group(2), _clean_city(cm.group(1), country), country
    return None, _clean_city(body, country), country


def _detect_type(name: str) -> str:
    low = name.lower()
    for market_type, keywords in _TYPE_KEYWORDS.items():
        if any(k in low for k in keywords):
            return market_type
    return "medieval"


def _parse_row(row: Tag) -> MarketData | None:
    cells = row.find_all("td")
    if len(cells) < 3:
        return None

    dates = _parse_dates(cells[0].get_text(" ", strip=True))
    if dates is None:
        return None
    start_date, end_date = dates

    link = cells[1].find("a", href=True)
    name_cell = link if isinstance(link, Tag) else cells[1]
    name = name_cell.get_text(" ", strip=True)
    if not name:
        return None

    postal_code, city, country = _parse_location(cells[2].get_text(" ", strip=True))
    if country not in _COUNTRIES or (postal_code is None and city is None):
        return None

    source_url = _URL
    if isinstance(link, Tag):
        href = link.get("href")
        if isinstance(href, str):
            source_url = urljoin(_URL, href)

    return MarketData(
        name=name[:200],
        start_date=start_date,
        end_date=end_date,
        city=city,
        postal_code=postal_code,
        country=country,
        market_type=_detect_type(name),
        source_url=source_url,
        confidence_score=0.85,
        original_text=row.get_text(" | ", strip=True)[:500],
    )


def parse_market_table(html: str, min_year: int) -> list[MarketData]:
    """Parse all DACH/LI/LU rows starting in *min_year* or later."""
    soup = BeautifulSoup(html, "lxml")
    results: list[MarketData] = []
    for row in soup.find_all("tr", attrs={"data-date": True}):
        mdata = _parse_row(row)
        if mdata and mdata.start_date.year >= min_year:
            results.append(mdata)
    return results


@register("fyndling")
class FyndlingAdapter(AbstractCrawlerAdapter):
    """Scraper for the fyndling.de market list (DACH, LI and LU rows only)."""

    SOURCE_NAME = "Fyndling.de"
    BASE_URL = _URL

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        try:
            response = await client.get(_URL)
            response.raise_for_status()
        except Exception as exc:
            logger.error("%s: page request failed: %s", self.SOURCE_NAME, exc)
            raise

        results = parse_market_table(response.text, date.today().year)
        logger.info("%s: scraped %d DACH/LI/LU events", self.SOURCE_NAME, len(results))
        return results
