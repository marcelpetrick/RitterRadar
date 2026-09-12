# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for mittelaltermarkt-info.de — hand-curated event lists per country.

The WordPress site keeps one long, chronologically sorted list per country.
Its REST API exposes no event data, so the adapter parses the pages for
Germany, Austria and Switzerland. robots.txt allows all crawling.

Page URLs:
    https://mittelaltermarkt-info.de/mittelaltermaerkte-in-deutschland/
    https://mittelaltermarkt-info.de/mittelalterliche-events-oesterreich/
    https://mittelaltermarkt-info.de/mittelalterliche-events-in-der-schweiz/

Entry structure (one paragraph per event, grouped under <h3> month headings):
    <p><strong>04.09. – 06.09. 2026, <a href="/event-pro/SLUG/">Name</a>,
       [Venue,] 89522 Heidenheim an der Brenz, Baden-Württemberg</strong></p>
    Some entries have no link: "11.09. – 13.09. 2026, Name, 19073 Wittenförden, …"

Date variants observed:
    "3.9. – 6.9. 2026"   "04.09. – 05.09. 2026"   "05.01. 2026"
    "12.12.- 13.12. 2026"   "10.10. bis 11.10.2026"   "17.-18.10.2026"
    "05. – 06.09.2026"
Location: postal code with optional "A-"/"CH-"/"D-" prefix; the last comma
part is the federal state or country name. Entries such as
"Termin 2026 noch nicht bekannt" carry no date and are skipped.

Verified: 2026-09-13.
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
_VERIFIED_DATE = "2026-09-13"

_BASE = "https://mittelaltermarkt-info.de"
PAGES: tuple[tuple[str, str], ...] = (
    ("DE", f"{_BASE}/mittelaltermaerkte-in-deutschland/"),
    ("AT", f"{_BASE}/mittelalterliche-events-oesterreich/"),
    ("CH", f"{_BASE}/mittelalterliche-events-in-der-schweiz/"),
)

_ENTRY_RE = re.compile(
    r"^(?P<d1>\d{1,2})\.(?:(?P<m1>\d{1,2})\.)?\s*"
    r"(?:(?:[–\-]|bis)\s*(?P<d2>\d{1,2})\.(?P<m2>\d{1,2})\.?\s*)?"
    r"(?P<year>\d{4})\s*,\s*(?P<rest>.+)$",
    re.DOTALL,
)
_POSTAL_CITY_RE = re.compile(r"^(?:[A-Z]{1,2}-)?(\d{4,5})\s+(.+)$")
_EVENT_LINK_RE = re.compile(r"/event-pro/")
_TYPE_KEYWORDS: dict[str, list[str]] = {
    "christmas": ["weihnacht", "advent", "rauhnacht", "raunacht"],
    "viking": ["wikinger", "viking"],
    "renaissance": ["renaissance"],
    "fantasy": ["fantasy", "annotopia"],
}


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_dates(m: re.Match[str]) -> tuple[date, date] | None:
    year = int(m.group("year"))
    d1 = int(m.group("d1"))
    m1 = int(m.group("m1")) if m.group("m1") else None
    if m.group("d2") is None:
        if m1 is None:
            return None
        single = _safe_date(year, m1, d1)
        return (single, single) if single else None

    d2, m2 = int(m.group("d2")), int(m.group("m2"))
    start_month = m1 if m1 is not None else m2
    # "27.12. – 02.01. 2027": the start lies in the previous year
    start_year = year - 1 if start_month > m2 else year
    start = _safe_date(start_year, start_month, d1)
    end = _safe_date(year, m2, d2)
    if start is None or end is None or end < start:
        return None
    return start, end


def _clean_city(city: str) -> str:
    city = re.sub(r"\s*\([^)]*\)$", "", city)  # "Neunkirchen (NÖ)"
    city = re.sub(r"\s+[A-Z]{2}$", "", city)  # Swiss canton suffix: "Laupen BE"
    return city.strip()


def _parse_location(parts: list[str]) -> tuple[str | None, str | None, str | None]:
    """Return (address, postal_code, city) from the comma parts after the name."""
    for i, part in enumerate(parts):
        pm = _POSTAL_CITY_RE.match(part)
        if pm:
            address = ", ".join(parts[:i]) or None
            return address, pm.group(1), _clean_city(pm.group(2)) or None
    # No postal code: "[Venue,] City, State/Country"
    if len(parts) >= 2:
        return ", ".join(parts[:-2]) or None, None, _clean_city(parts[-2]) or None
    return None, None, None


def _detect_type(name: str) -> str:
    low = name.lower()
    for market_type, keywords in _TYPE_KEYWORDS.items():
        if any(k in low for k in keywords):
            return market_type
    return "medieval"


def _parse_paragraph(p: Tag, country: str, page_url: str) -> MarketData | None:
    text = p.get_text(" ", strip=True).replace("\xa0", " ")
    m = _ENTRY_RE.match(text)
    if not m:
        return None
    dates = _parse_dates(m)
    if dates is None:
        return None

    rest = m.group("rest")
    link = p.find("a", href=_EVENT_LINK_RE)
    source_url = page_url
    if isinstance(link, Tag):
        name = link.get_text(" ", strip=True)
        href = link.get("href")
        if isinstance(href, str):
            source_url = href
        tail = rest.split(name, 1)[-1] if name in rest else rest
    else:
        name, _, tail = rest.partition(",")
        name = name.strip()
    if not name:
        return None

    parts = [x.strip() for x in tail.split(",") if x.strip()]
    address, postal_code, city = _parse_location(parts)
    if postal_code is None and city is None:
        return None

    return MarketData(
        name=name[:200],
        start_date=dates[0],
        end_date=dates[1],
        address=address,
        city=city,
        postal_code=postal_code,
        country=country,
        market_type=_detect_type(name),
        source_url=source_url,
        confidence_score=0.85,
        original_text=text[:500],
    )


def parse_event_page(html: str, country: str, page_url: str) -> list[MarketData]:
    """Parse every dated event paragraph of one country page."""
    soup = BeautifulSoup(html, "lxml")
    article = soup.find("article")
    container = article if isinstance(article, Tag) else soup
    results: list[MarketData] = []
    for p in container.find_all("p"):
        mdata = _parse_paragraph(p, country, page_url)
        if mdata:
            results.append(mdata)
    return results


@register("mittelaltermarkt_info")
class MittelaltermarktInfoAdapter(AbstractCrawlerAdapter):
    """Scraper for the DE/AT/CH event lists on mittelaltermarkt-info.de."""

    SOURCE_NAME = "Mittelaltermarkt-info.de"
    BASE_URL = PAGES[0][1]

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        results: list[MarketData] = []
        this_year = date.today().year
        for country, url in PAGES:
            try:
                response = await client.get(url)
                response.raise_for_status()
            except Exception:
                logger.warning("%s: failed to fetch %s", self.SOURCE_NAME, url)
                continue
            # Pages can still list last year's entries (seen on the Swiss page)
            events = [
                e
                for e in parse_event_page(response.text, country, url)
                if e.start_date.year >= this_year
            ]
            logger.info("%s: %d events on %s page", self.SOURCE_NAME, len(events), country)
            results.extend(events)

        logger.info("%s: scraped %d events total", self.SOURCE_NAME, len(results))
        return results
