# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Adapter for vehi-mercatus.de Mittelalter-Marktkalender.

Page structure (verified 2026-06-25):
  URL: /marktkalender/?ansicht=liste&land=Deutschland&jahr={YEAR}&seite={N}
  Count info: <div class="mk-event-count"> "287 Events – Seite 1 von 6"
  Each event: <div class="mk-compact-row"> with 4–5 child divs:
    [0] date  e.g. "26.02.–01.03.2026" or "06.–08.03.2026" or "29.05.2026"
    [1] name  e.g. "Kieler UmschlagFrei"  ("Frei" = free entry suffix)
    [2] loc   e.g. "24103 Kiel, Sch."
    [3] type  e.g. "Mittelaltermarkt"

Date formats observed:
  DD.MM.YYYY                     (single day)
  DD.–DD.MM.YYYY                 (same-month range)
  DD.MM.–DD.MM.YYYY              (cross-month range)
  DD.MM.YYYY–DD.MM.YYYY         (rare full-date both sides)
"""

__version__ = "0.1.0"
_VERIFIED_DATE = "2026-06-25"

import logging
import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register

logger = logging.getLogger(__name__)

BASE = "https://vehi-mercatus.de"

# Type mapping from site's own categories
_TYPE_MAP = {
    "Mittelaltermarkt":              "medieval",
    "Mittelalterfest":               "medieval",
    "Mittelalterspektakel":          "medieval",
    "Spektakulum":                   "medieval",
    "Ritterfest":                    "medieval",
    "Ritterturnier":                 "medieval",
    "Burgfest":                      "medieval",
    "Stadtfest":                     "medieval",
    "Freilichttheater":              "medieval",
    "Wikingerspektakel":             "viking",
    "LARP-Event":                    "fantasy",
    "Mittelalterlicher Weihnachtsmarkt": "christmas",
    "Mittelalter-Rock-Festival":     "medieval",
}

# Regex for the various date formats
# Group 1: start day, Group 2: start month (may be missing), Group 3: end day,
# Group 4: end month, Group 5: year
_RANGE_RE = re.compile(
    r"(\d{1,2})\."         # start day
    r"(?:(\d{2})\.)?"      # optional start month
    r"[–-]"                # en-dash or hyphen separator
    r"(\d{1,2})\."         # end day
    r"(\d{2})\."           # end month
    r"(\d{4})"             # year
)
# Single day: DD.MM.YYYY
_SINGLE_RE = re.compile(r"(\d{1,2})\.(\d{2})\.(\d{4})")

# Strip "Frei" / "Gratis" free-entry suffixes that appear in event names
_FREE_SUFFIX_RE = re.compile(r"(Frei|Gratis)$")

# Extract PLZ from location string "12345 City, State"
_PLZ_RE = re.compile(r"^(\d{4,5})\s+(.+?)(?:,.*)?$")


def _parse_date_field(text: str) -> tuple[date, date] | None:
    text = text.strip()
    m = _RANGE_RE.search(text)
    if m:
        sd, sm, ed, em, y = m.groups()
        start_month = sm if sm else em   # borrow end month if start month absent
        try:
            start = date(int(y), int(start_month), int(sd))
            end   = date(int(y), int(em), int(ed))
            return start, end
        except ValueError:
            pass
    m = _SINGLE_RE.search(text)
    if m:
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return d, d
        except ValueError:
            pass
    return None


def _parse_location(text: str) -> tuple[str | None, str | None]:
    """Return (postal_code, city) from '24103 Kiel, Sch.'"""
    m = _PLZ_RE.match(text.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return None, text.strip() or None


def _page_url(year: int, page: int) -> str:
    return (
        f"{BASE}/marktkalender/?ansicht=liste"
        f"&land=Deutschland&jahr={year}&seite={page}"
    )


def _map_type(site_type: str) -> str:
    return _TYPE_MAP.get(site_type.strip(), "medieval")


@register("vehi_mercatus")
class VehiMercatusAdapter(AbstractCrawlerAdapter):
    """Scraper for vehi-mercatus.de Mittelalter-Marktkalender (DE events)."""

    SOURCE_NAME = "Vehi Mercatus Marktkalender"
    BASE_URL = BASE

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        results: list[MarketData] = []
        today = date.today()

        for year in (today.year, today.year + 1):
            for page in range(1, 20):  # safety cap; real max ~11 pages
                url = _page_url(year, page)
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                except Exception:
                    logger.warning("%s: failed page %d/%d", self.SOURCE_NAME, year, page)
                    break

                soup = BeautifulSoup(response.text, "lxml")
                rows = soup.find_all(class_="mk-compact-row")
                if not rows:
                    break

                for row in rows:
                    date_el = row.find(class_="mk-compact-col-date")
                    name_el = row.find(class_="mk-compact-col-name")
                    loc_el  = row.find(class_="mk-compact-col-location")
                    type_el = row.find(class_="mk-compact-col-type")
                    if not (date_el and name_el):
                        continue

                    date_text = date_el.get_text(strip=True)
                    name_raw  = name_el.get_text(strip=True)
                    loc_text  = loc_el.get_text(strip=True) if loc_el else ""
                    type_text = type_el.get_text(strip=True) if type_el else ""

                    dates = _parse_date_field(date_text)
                    if not dates:
                        continue

                    name = _FREE_SUFFIX_RE.sub("", name_raw).strip()
                    if not name:
                        continue

                    postal_code, city = _parse_location(loc_text)
                    # The row itself is an <a> tag with the detail URL
                    href = row.get("href", "") if row.name == "a" else ""
                    if not href:
                        link = row.find("a", href=True)
                        href = link["href"] if link else ""
                    source_url = (BASE + href) if href and not href.startswith("http") else (href or f"{BASE}/marktkalender/")

                    results.append(
                        MarketData(
                            name=name[:200],
                            start_date=dates[0],
                            end_date=dates[1],
                            city=city,
                            postal_code=postal_code,
                            source_url=source_url,
                            market_type=_map_type(type_text),
                            confidence_score=0.9,
                            original_text=f"{date_text} | {name} | {loc_text} | {type_text}"[:500],
                        )
                    )

                # Check if there are more pages
                count_el = soup.find(class_="mk-event-count")
                if count_el:
                    text = count_el.get_text()
                    m = re.search(r"Seite\s+(\d+)\s+von\s+(\d+)", text)
                    if m and int(m.group(1)) >= int(m.group(2)):
                        break
                elif len(rows) < 50:
                    break

            logger.info(
                "%s: scraped %d events so far (after year %d)",
                self.SOURCE_NAME, len(results), year,
            )

        logger.info("%s: scraped %d events total", self.SOURCE_NAME, len(results))
        return results
