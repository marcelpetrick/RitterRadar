# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for the mittelaltermarkt-info.de adapter (offline HTML fixtures)."""

from datetime import date

import pytest

from ritterradar.crawler.adapters.mittelaltermarkt_info import (
    PAGES,
    MittelaltermarktInfoAdapter,
    parse_event_page,
)
from tests.crawler.fake_client import FakeClient

_PAGE = "https://mittelaltermarkt-info.de/mittelaltermaerkte-in-deutschland/"
_EV = "https://mittelaltermarkt-info.de/event-pro"


def _html(*paragraphs: str) -> str:
    body = "".join(f"<p><strong>{p}</strong></p>" for p in paragraphs)
    return f"<article><h3>September 2026</h3><p>Einleitung 2026.</p>{body}</article>"


def _one(paragraph: str, country: str = "DE"):
    results = parse_event_page(_html(paragraph), country, _PAGE)
    assert len(results) == 1, results
    return results[0]


@pytest.mark.parametrize(
    ("prefix", "start", "end"),
    [
        ("3.9. &#8211; 6.9. 2026", date(2026, 9, 3), date(2026, 9, 6)),
        ("04.09. – 05.09. 2026", date(2026, 9, 4), date(2026, 9, 5)),
        ("05.01. 2026", date(2026, 1, 5), date(2026, 1, 5)),
        ("12.12.- 13.12. 2026", date(2026, 12, 12), date(2026, 12, 13)),
        ("10.10. bis 11.10.2026", date(2026, 10, 10), date(2026, 10, 11)),
        ("17.-18.10.2026", date(2026, 10, 17), date(2026, 10, 18)),
        ("05. – 06.09.2026", date(2026, 9, 5), date(2026, 9, 6)),
        ("27.12. – 02.01. 2027", date(2026, 12, 27), date(2027, 1, 2)),
    ],
)
def test_date_variants(prefix, start, end):
    event = _one(f'{prefix}, <a href="{_EV}/x/">Markt</a>, 34497 Korbach, Hessen')
    assert (event.start_date, event.end_date) == (start, end)


def test_linked_entry_with_venue():
    event = _one(
        f'04.9. &#8211; 06.9. 2026, <a href="{_EV}/heidenheim/">Mittelaltermarkt zu Heidenheim</a>'
        ", Schloss Hellenstein, 89522 Heidenheim an der Brenz, Baden-Württemberg"
    )
    assert event.name == "Mittelaltermarkt zu Heidenheim"
    assert event.address == "Schloss Hellenstein"
    assert (event.postal_code, event.city, event.country) == (
        "89522",
        "Heidenheim an der Brenz",
        "DE",
    )
    assert event.source_url == f"{_EV}/heidenheim/"


def test_unlinked_entry_uses_page_url():
    event = _one("11.09. – 13.09. 2026, Mittelalter-Spektakel Wittenförden, 19073 Wittenförden, MV")
    assert event.name == "Mittelalter-Spektakel Wittenförden"
    assert (event.postal_code, event.city) == ("19073", "Wittenförden")
    assert event.source_url == _PAGE


def test_austrian_and_swiss_locations():
    at = _one(
        f'5.12. – 6.12. 2026, <a href="{_EV}/p/">Adventmarkt auf Burg Plankenstein</a>'
        ", Burg Plankenstein, A-3242 Plankenstein, Österreich",
        country="AT",
    )
    assert (at.postal_code, at.city, at.country, at.market_type) == (
        "3242",
        "Plankenstein",
        "AT",
        "christmas",
    )
    ch = _one(
        f'10.04. – 12.04. 2026, <a href="{_EV}/l/">Mittelalterfest Schloss Laupen</a>'
        ", 3177 Laupen BE, Schweiz",
        country="CH",
    )
    assert (ch.postal_code, ch.city) == ("3177", "Laupen")
    no_plz = _one(
        f'9.10. – 11.10. 2026, <a href="{_EV}/w/">Halloween Spektakel</a>'
        ", Teuchelweiherplatz, Winterthur, Schweiz",
        country="CH",
    )
    assert (no_plz.postal_code, no_plz.city, no_plz.address) == (
        None,
        "Winterthur",
        "Teuchelweiherplatz",
    )


def test_undated_and_non_event_paragraphs_are_skipped():
    html = _html(
        f'Termin 2026 noch nicht bekannt, <a href="{_EV}/s/">Klostermarkt</a>, 8260 Stein, Schweiz',
        "31.02. 2026, Unmögliches Datum, 12345 Nirgendwo, Hessen",
    )
    assert parse_event_page(html, "CH", _PAGE) == []


async def test_crawl_fetches_all_country_pages_and_drops_past_years():
    year = date.today().year
    de_url = PAGES[0][1]
    page = _html(
        f"05.01. {year}, Raunacht, 01067 Dresden, Sachsen",
        f"12.09. – 14.09. {year - 1}, Vorjahresmarkt, 8215 Hallau, Schweiz",
    )
    client = FakeClient({de_url: page})
    results = await MittelaltermarktInfoAdapter().crawl(client)  # type: ignore[arg-type]
    assert client.requested == [url for _, url in PAGES]
    assert [r.name for r in results] == ["Raunacht"]
