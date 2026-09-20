# SPDX-License-Identifier: GPL-3.0-or-later
"""Location formats encountered in September 2026 live crawls."""

from datetime import date

import pytest
from bs4 import BeautifulSoup

from ritterradar.crawler.adapters import marktkalendarium, mittelaltermarkt_online, spectaculum
from ritterradar.crawler.adapters.trollfelsen import _parse_location
from tests.crawler.fake_client import FakeClient


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("NL - 5944 BE Arcen", ("5944 BE", "Arcen", "NL")),
        ("DE - 06217 Merseburg", ("06217", "Merseburg", "DE")),
        ("AT - 5020 Salzburg | Altstadt", ("5020", "Salzburg", "AT")),
    ],
)
def test_trollfelsen_postcodes(text, expected):
    assert _parse_location(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Störmede (wo immer das auch sein mag)", (None, "Störmede", "DE")),
        ("Bad Liebenzell", (None, "Bad Liebenzell", "DE")),
        ("Chiemsee", (None, "Chiemsee", "DE")),
        ("CH-5600 Lenzburg", ("5600", "Lenzburg", "CH")),
        ("D-<b>46325</b> Borken", ("46325", "Borken", "DE")),
    ],
)
def test_marktkalendarium_preserves_places_without_postcodes(text, expected):
    cell = BeautifulSoup(f"<td>{text}</td>", "lxml").td
    assert marktkalendarium._parse_location(cell) == expected


async def test_spectaculum_separates_festival_brand_from_city():
    client = FakeClient(
        {spectaculum.BASE: ('<a href="/termine/borken/">26.09. + 27.09.2026 Retro MPS Borken</a>')}
    )
    results = await spectaculum.SpectaculumAdapter().crawl(client)
    assert len(results) == 1
    assert results[0].city == "Borken"
    assert results[0].start_date == date(2026, 9, 26)


@pytest.mark.parametrize(
    ("country", "expected"),
    [
        ("Frankreich", "FR"),
        ("France", "FR"),
        ("Niederlande", "NL"),
        ("CH", "CH"),
        ("ch", "CH"),
        ("Schweiz", "CH"),
    ],
)
def test_rest_calendar_preserves_foreign_countries(country, expected):
    event = mittelaltermarkt_online._parse_event(
        {
            "title": "Mittelaltermarkt",
            "start_date": "2026-09-25 10:00:00",
            "end_date": "2026-09-27 18:00:00",
            "venue": {"country": country},
        }
    )
    assert event.country == expected


def test_marktkalendarium_rejects_reversed_source_dates():
    row = BeautifulSoup(
        "<table><tr><td>17.9.2027</td><td>19.8.2027</td>"
        "<td>Zeitsprung ins Mittelalter Altstadtfest</td><td>D-12345 Teststadt</td>"
        "<td>Altstadt</td><td>https://example.com</td></tr></table>",
        "lxml",
    ).tr
    assert marktkalendarium._parse_row(row) is None
