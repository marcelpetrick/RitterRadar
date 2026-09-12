# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for the fyndling.de adapter (offline HTML fixtures)."""

from datetime import date

from ritterradar.crawler.adapters.fyndling import (
    _URL,
    FyndlingAdapter,
    _parse_location,
    parse_market_table,
)
from tests.crawler.fake_client import FakeClient

_HTML = """
<table>
<tr><th>Datum</th><th>Veranstaltung</th><th>Ort</th></tr>
<tr class="month-heading"><td colspan="3">Januar 2026</td></tr>
<tr data-date="2026-01-02" id="a1"><td>02.01.2026 - 04.01.2026</td>
  <td><a href="https://fyndling.de/e/a1">3.Eisenbacher Rauhnachtsmarkt</a> </td>
  <td>63785 Obernburg am Main</td></tr>
<tr data-date="2026-01-04" id="a2"><td>04.01.2026</td>
  <td><a href="https://fyndling.de/e/a2">Marché Historique</a></td>
  <td>21700 Nuits-Saint-Georges (🇫🇷FR)</td></tr>
<tr data-date="2026-04-18" id="a3"><td>18.04.2026 - 19.04.2026</td>
  <td><a href="/e/a3">18. Wikingerfest am Kiessee Schildow</a></td>
  <td>5710 Kaprun (🇦🇹AT)</td></tr>
<tr data-date="2026-05-01" id="a4"><td>01.05.2026</td>
  <td><a href="https://fyndling.de/e/a4">Burgfest</a></td>
  <td>Martigny (🇨🇭CH)</td></tr>
<tr data-date="2026-06-01" id="a5"><td>01.06.2026</td>
  <td><a href="https://fyndling.de/e/a5">Ohne Ort</a></td>
  <td>(🇦🇹AT)</td></tr>
<tr data-date="2025-12-30" id="a6"><td>30.12.2025</td>
  <td><a href="https://fyndling.de/e/a6">Vorjahr</a></td>
  <td>01067 Dresden</td></tr>
</table>
"""


def test_parse_market_table_keeps_dach_rows_with_location():
    results = parse_market_table(_HTML, min_year=2026)
    assert [r.name for r in results] == [
        "3.Eisenbacher Rauhnachtsmarkt",
        "18. Wikingerfest am Kiessee Schildow",
        "Burgfest",
    ]

    first = results[0]
    assert (first.start_date, first.end_date) == (date(2026, 1, 2), date(2026, 1, 4))
    assert (first.postal_code, first.city, first.country) == ("63785", "Obernburg am Main", "DE")
    assert first.market_type == "christmas"
    assert first.source_url == "https://fyndling.de/e/a1"

    viking = results[1]
    assert viking.country == "AT"
    assert viking.market_type == "viking"
    assert viking.source_url == "https://fyndling.de/e/a3"

    swiss = results[2]
    assert (swiss.postal_code, swiss.city, swiss.country) == (None, "Martigny", "CH")
    assert swiss.start_date == swiss.end_date == date(2026, 5, 1)


def test_parse_location_variants():
    assert _parse_location("01067 Dresden") == ("01067", "Dresden", "DE")
    assert _parse_location("95671") == ("95671", None, "DE")
    assert _parse_location("L-7610 Larochette (🇱🇺LU)") == ("7610", "Larochette", "LU")
    assert _parse_location("YO1 9WT York (🇬🇧GB)") == (None, "YO1 9WT York", "GB")


async def test_crawl_uses_market_page():
    client = FakeClient({_URL: _HTML})
    results = await FyndlingAdapter().crawl(client)  # type: ignore[arg-type]
    assert client.requested == [_URL]
    assert all(r.start_date.year >= date.today().year for r in results)
