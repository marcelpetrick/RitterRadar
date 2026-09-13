# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Offline fixture tests for the long-standing active crawler adapters."""

import json
from datetime import date

import pytest

from ritterradar.crawler.adapters import (
    marktkalendarium,
    mittelaltermarkt_online,
    spectaculum,
    taterman_at,
    trollfelsen,
    vehi_mercatus,
)
from tests.crawler.fake_client import FakeClient

Y = date.today().year


# ── Taterman.at (iCal) ──────────────────────────────────────────────────


def _ical(*events: str) -> str:
    body = "\r\n".join(events)
    return f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n{body}\r\nEND:VCALENDAR\r\n"


def _vevent(uid: str, *lines: str) -> str:
    return "\r\n".join(["BEGIN:VEVENT", f"UID:{uid}@test", *lines, "END:VEVENT"])


async def test_taterman_parses_all_day_timed_and_open_ended_events():
    feed = _ical(
        _vevent(
            "advent",
            "SUMMARY:Adventmarkt Burg Kreuzenstein",
            f"DTSTART;TZID=Europe/Vienna;VALUE=DATE:{Y}0712",
            f"DTEND;TZID=Europe/Vienna;VALUE=DATE:{Y}0714",
            "LOCATION:Burg Kreuzenstein\\, Leobendorf\\, 2105\\, Österreich",
            "URL:https://www.taterman.at/termin/kreuzenstein/",
        ),
        _vevent(
            "viking",
            "SUMMARY:Wikingertreffen",
            f"DTSTART:{Y}0501T100000",
            f"DTEND:{Y}0501T180000",
            "LOCATION:Niederösterreich\\, 3100\\, Österreich",
        ),
        _vevent(
            "graz",
            "SUMMARY:Renaissancefest Graz",
            f"DTSTART;VALUE=DATE:{Y}0808",
            "LOCATION:Graz\\, Österreich",
        ),
        _vevent("old", "SUMMARY:Altes Fest", f"DTSTART;VALUE=DATE:{Y - 3}0101"),
        _vevent("nameless", f"DTSTART;VALUE=DATE:{Y}0601"),
        _vevent("undated", "SUMMARY:Ohne Datum"),
    )
    client = FakeClient({taterman_at._FEED_URL: feed})
    results = await taterman_at.TatermanAtAdapter().crawl(client)  # type: ignore[arg-type]

    assert [r.name for r in results] == [
        "Adventmarkt Burg Kreuzenstein",
        "Wikingertreffen",
        "Renaissancefest Graz",
    ]
    advent, viking, graz = results
    assert (advent.start_date, advent.end_date) == (date(Y, 7, 12), date(Y, 7, 13))
    assert (advent.city, advent.postal_code, advent.market_type) == (
        "Leobendorf",
        "2105",
        "christmas",
    )
    assert advent.source_url == "https://www.taterman.at/termin/kreuzenstein/"
    assert (viking.start_date, viking.end_date) == (date(Y, 5, 1), date(Y, 5, 1))
    assert (viking.city, viking.postal_code, viking.market_type) == (None, "3100", "viking")
    assert viking.source_url == taterman_at.TatermanAtAdapter.BASE_URL
    assert (graz.end_date, graz.city, graz.market_type) == (date(Y, 8, 8), "Graz", "renaissance")
    assert all(r.country == "AT" for r in results)


def test_taterman_helpers():
    assert taterman_at._parse_location("") == (None, None)
    assert taterman_at._parse_location("Steiermark, Österreich") == (None, None)
    assert taterman_at._coerce_date("not a date") is None
    assert taterman_at._detect_type("Fantasy Festival") == "fantasy"


async def test_taterman_feed_errors_are_raised():
    with pytest.raises(RuntimeError):
        await taterman_at.TatermanAtAdapter().crawl(FakeClient({}))  # type: ignore[arg-type]
    broken = FakeClient({taterman_at._FEED_URL: "BEGIN:VCALENDAR\r\nthis is not ical"})
    with pytest.raises(ValueError, match="iCal parse failed"):
        await taterman_at.TatermanAtAdapter().crawl(broken)  # type: ignore[arg-type]


# ── Mittelaltermarkt.online (REST API) ──────────────────────────────────


def _api_url(page: int) -> str:
    return (
        f"{mittelaltermarkt_online._API_URL}?per_page=100&status=publish"
        f"&start_date={Y}-01-01&end_date={Y + 1}-12-31&page={page}"
    )


async def test_mittelaltermarkt_online_reads_all_pages():
    page1 = {
        "total": 4,
        "total_pages": 2,
        "events": [
            {
                "title": "Ritterfest &#8211; Burg Kiel",
                "start_date": f"{Y}-06-01 10:00:00",
                "end_date": f"{Y}-06-02 18:00:00",
                "url": "https://mittelaltermarkt.online/event/kiel/",
                "venue": {
                    "city": "Kiel",
                    "zip": " 24103 ",
                    "country": "Deutschland",
                    "geo_lat": 54.32,
                    "geo_lng": 10.13,
                },
                "categories": [{"slug": "mittelalterfeste"}],
            },
            {
                "title": "Wintermarkt Wien",
                "start_date": f"{Y}-12-01 10:00:00",
                "end_date": "",
                "venue": {"city": "Wien", "zip": "n/a", "country": "Österreich"},
                "categories": [{"slug": "adventsmarkt-wien"}],
            },
            {"title": "", "start_date": f"{Y}-01-01 00:00:00"},
            {"title": "Kaputtes Datum", "start_date": "demnächst"},
        ],
    }
    page2 = {
        "events": [
            {
                "title": "Nordmannfest",
                "start_date": f"{Y}-08-01 10:00:00",
                "end_date": f"{Y}-08-02 10:00:00",
                "venue": None,
                "categories": [{"slug": "wikinger-lager"}],
            }
        ]
    }
    client = FakeClient({_api_url(1): json.dumps(page1), _api_url(2): json.dumps(page2)})
    adapter = mittelaltermarkt_online.MittelaltermarktOnlineAdapter()
    results = await adapter.crawl(client)  # type: ignore[arg-type]

    assert [r.name for r in results] == [
        "Ritterfest – Burg Kiel",
        "Wintermarkt Wien",
        "Nordmannfest",
    ]
    kiel, wien, nord = results
    assert (kiel.postal_code, kiel.latitude, kiel.longitude, kiel.market_type) == (
        "24103",
        54.32,
        10.13,
        "medieval",
    )
    assert (wien.country, wien.postal_code, wien.end_date, wien.market_type) == (
        "AT",
        None,
        date(Y, 12, 1),
        "christmas",
    )
    assert (nord.country, nord.city, nord.market_type) == ("DE", None, "viking")
    assert nord.source_url == mittelaltermarkt_online.BASE


@pytest.mark.parametrize(
    ("slug", "expected"),
    [
        ("weihnachtsmaerkte", "christmas"),
        ("fantasy-convention", "fantasy"),
        ("renaissance-abend", "renaissance"),
        ("viking-camp", "viking"),
        ("ritterturniere", "medieval"),
    ],
)
def test_mittelaltermarkt_online_category_types(slug, expected):
    assert mittelaltermarkt_online._detect_type([{"slug": slug}]) == expected


async def test_mittelaltermarkt_online_stops_on_errors():
    adapter = mittelaltermarkt_online.MittelaltermarktOnlineAdapter()
    assert await adapter.crawl(FakeClient({})) == []  # type: ignore[arg-type]
    assert await adapter.crawl(FakeClient({_api_url(1): "<html>"})) == []  # type: ignore[arg-type]


# ── Vehi Mercatus (paginated HTML) ──────────────────────────────────────


def _vm_row(date_text: str, name: str, loc: str = "24103 Kiel, Sch.", **kw: str) -> str:
    typ = kw.get("typ", "Mittelaltermarkt")
    href = kw.get("href", "/marktkalender/eintrag/")
    spans = (
        f'<span class="mk-compact-col-date">{date_text}</span>'
        f'<span class="mk-compact-col-name">{name}</span>'
        f'<span class="mk-compact-col-location">{loc}</span>'
        f'<span class="mk-compact-col-type">{typ}</span>'
    )
    if kw.get("tag") == "div":
        return f'<div class="mk-compact-row"><a href="{href}">Details</a>{spans}</div>'
    return f'<a class="mk-compact-row" href="{href}">{spans}</a>'


async def test_vehi_mercatus_follows_pagination_and_parses_rows():
    page_1 = "".join(
        [
            _vm_row(f"06.–08.03.{Y}", "Kieler UmschlagFrei"),
            _vm_row(
                f"26.02.–01.03.{Y}",
                "Wikingertreffen",
                typ="Wikingerspektakel",
                href="https://example.org/wikinger",
            ),
            _vm_row(f"29.05.{Y}", "Burgfest", loc="Irgendwo", tag="div", href="/detail/burg/"),
            _vm_row("demnächst", "Ohne Datum"),
            _vm_row(f"01.06.{Y}", "Frei"),
            f'<a class="mk-compact-row"><span class="mk-compact-col-date">01.06.{Y}</span></a>',
            '<div class="mk-event-count">Seite 1 von 2</div>',
        ]
    )
    page_2 = (
        _vm_row(f"12.09.{Y}", "Herbstmarkt") + '<div class="mk-event-count">Seite 2 von 2</div>'
    )
    next_year = _vm_row(f"01.05.{Y + 1}", "Maimarkt", href="")
    client = FakeClient(
        {
            vehi_mercatus._page_url(Y, 1): page_1,
            vehi_mercatus._page_url(Y, 2): page_2,
            vehi_mercatus._page_url(Y + 1, 1): next_year,
        }
    )
    results = await vehi_mercatus.VehiMercatusAdapter().crawl(client)  # type: ignore[arg-type]

    assert [r.name for r in results] == [
        "Kieler Umschlag",
        "Wikingertreffen",
        "Burgfest",
        "Herbstmarkt",
        "Maimarkt",
    ]
    umschlag, wikinger, burg, _, mai = results
    assert (umschlag.start_date, umschlag.end_date) == (date(Y, 3, 6), date(Y, 3, 8))
    assert (umschlag.postal_code, umschlag.city) == ("24103", "Kiel")
    assert umschlag.source_url == f"{vehi_mercatus.BASE}/marktkalender/eintrag/"
    assert (wikinger.start_date, wikinger.end_date) == (date(Y, 2, 26), date(Y, 3, 1))
    assert (wikinger.market_type, wikinger.source_url) == ("viking", "https://example.org/wikinger")
    assert (burg.postal_code, burg.city, burg.source_url) == (
        None,
        "Irgendwo",
        f"{vehi_mercatus.BASE}/detail/burg/",
    )
    assert mai.source_url == f"{vehi_mercatus.BASE}/marktkalender/"


def test_vehi_mercatus_date_field_variants():
    assert vehi_mercatus._parse_date_field(f"31.02.–01.03.{Y}") == (date(Y, 3, 1), date(Y, 3, 1))
    assert vehi_mercatus._parse_date_field(f"31.02.{Y}") is None
    assert vehi_mercatus._parse_date_field("bald") is None


async def test_vehi_mercatus_survives_unreachable_pages():
    assert await vehi_mercatus.VehiMercatusAdapter().crawl(FakeClient({})) == []  # type: ignore[arg-type]


# ── Pfalzis Marktkalendarium (HTML table) ───────────────────────────────


def _mk_row(start: str, end: str, name: str, loc: str, website: str) -> str:
    return (
        f"<tr><td>{start}</td><td>{end}</td><td>{name}</td>"
        f"<td><a href='https://maps.google.de/maps?q={loc}'>{loc}</a></td>"
        f"<td>Innenstadt</td><td>{website}</td><td></td></tr>"
    )


async def test_marktkalendarium_parses_rows_and_skips_invalid_ones():
    website = (
        "<a href='https://maps.google.de/x'>Karte</a><a href='https://burgfest.example/'>Web</a>"
    )
    page = (
        "<table><tr><th>Beginn</th></tr>"
        + "".join(
            [
                _mk_row(f"6.6.{Y}", f"7.6.{Y}", "Burgfest Alzey", "D-55232 Alzey", website),
                _mk_row(
                    f"1.12.{Y}",
                    "",
                    "Weihnachtsmarkt Wien",
                    "A-1010 Wien",
                    "<a href='mailto:x@y'>M</a>",
                ),
                _mk_row(f"3.3.{Y}", f"4.3.{Y}", "Wikingerlager", "CH-8001 Zürich", ""),
                _mk_row(f"5.5.{Y}", f"5.5.{Y}", "Ohne Postleitzahl", "Musterstadt", ""),
                _mk_row(f"31.02.{Y}", f"1.3.{Y}", "Unmöglich", "D-12345 X", ""),
                _mk_row(f"8.8.{Y}", f"8.8.{Y}", "", "D-12345 X", ""),
                f"<tr><td>9.9.{Y}</td><td>zu wenige Zellen</td></tr>",
            ]
        )
        + "</table>"
    )
    client = FakeClient({f"{marktkalendarium.BASE}/maerkte{Y}.php": page})
    results = await marktkalendarium.MarktkalendariumAdapter().crawl(client)  # type: ignore[arg-type]

    assert [r.name for r in results] == [
        "Burgfest Alzey",
        "Weihnachtsmarkt Wien",
        "Wikingerlager",
        "Ohne Postleitzahl",
    ]
    alzey, wien, zuerich, ohne = results
    assert (alzey.country, alzey.postal_code, alzey.city) == ("DE", "55232", "Alzey")
    assert alzey.source_url == "https://burgfest.example/"
    assert (wien.country, wien.end_date, wien.market_type, wien.source_url) == (
        "AT",
        date(Y, 12, 1),
        "christmas",
        marktkalendarium.BASE,
    )
    assert (zuerich.country, zuerich.market_type) == ("CH", "viking")
    assert (ohne.postal_code, ohne.city) == (None, None)


# ── Trollfelsen.de (event cards) ────────────────────────────────────────


def _card(name: str, dates: str, location: str = "DE - 06217 Merseburg", **kw: str) -> str:
    h3 = f"<h3>{name}</h3>" if name else ""
    link = kw.get("link", "https://event.example/")
    return (
        f'<div class="event-card"><div class="picture"><a href="{link}">Bild</a></div>'
        f'<div class="infos">{h3}<div><div class="font-weight-bold">{dates}</div></div>'
        f"<div>Venue</div><div>{location}</div>{kw.get('extra', '')}</div></div>"
    )


async def test_trollfelsen_keeps_confirmed_current_events():
    page = "".join(
        [
            _card("Merseburger Markt", f"01.05.{Y} - 03.05.{Y}"),
            _card(
                "Unbestätigt",
                f"01.06.{Y} - 02.06.{Y}",
                extra="<div>* Teilnahme noch nicht bestätigt</div>",
            ),
            _card("", f"01.07.{Y} - 02.07.{Y}"),
            _card("Ohne Datum", "demnächst"),
            _card("Vorjahr", f"01.07.{Y - 1} - 02.07.{Y - 1}"),
            _card(
                "Salzburg",
                f"05.09.{Y} - 06.09.{Y}",
                "AT - 5020 Salzburg | Altstadt",
                link="/intern",
            ),
            _card("Ohne Ort", f"10.10.{Y} - 11.10.{Y}", "irgendwo"),
        ]
    )
    client = FakeClient({trollfelsen._URL: page})
    results = await trollfelsen.TrollfelsensAdapter().crawl(client)  # type: ignore[arg-type]

    assert [r.name for r in results] == ["Merseburger Markt", "Salzburg", "Ohne Ort"]
    merseburg, salzburg, ohne = results
    assert (merseburg.postal_code, merseburg.city, merseburg.source_url) == (
        "06217",
        "Merseburg",
        "https://event.example/",
    )
    assert (salzburg.country, salzburg.city, salzburg.source_url) == (
        "AT",
        "Salzburg",
        trollfelsen._URL,
    )
    assert (ohne.postal_code, ohne.city, ohne.country) == (None, None, "DE")


async def test_trollfelsen_errors_and_invalid_dates():
    assert trollfelsen._parse_date_range(f"31.02.{Y} - 01.03.{Y}") is None
    with pytest.raises(RuntimeError):
        await trollfelsen.TrollfelsensAdapter().crawl(FakeClient({}))  # type: ignore[arg-type]


# ── Spectaculum.de (navigation links) ───────────────────────────────────


async def test_spectaculum_parses_navigation_links():
    page = f"""
      <a href="/termine/bueckeburg_1/">25.07. + 26.07.{Y}Bückeburg 1</a>
      <a href="/termine/bueckeburg_1/">duplicate</a>
      <a href="/termine/weil/">14.08. - 16.08.{Y} Weil am Rhein</a>
      <a href="/termine/folgen/">Termine folgen</a>
      <a href="/termine/ungueltig/">31.02. - 01.03.{Y}Nirgendwo</a>
      <a href="/kontakt/">Kontakt</a>
    """
    client = FakeClient({spectaculum.BASE: page})
    results = await spectaculum.SpectaculumAdapter().crawl(client)  # type: ignore[arg-type]

    assert [(r.name, r.city) for r in results] == [
        ("MPS Bückeburg", "Bückeburg"),
        ("MPS Weil am Rhein", "Weil am Rhein"),
    ]
    assert (results[0].start_date, results[0].end_date) == (date(Y, 7, 25), date(Y, 7, 26))
    assert results[0].source_url == f"{spectaculum.BASE}/termine/bueckeburg_1/"


async def test_spectaculum_returns_empty_list_when_homepage_fails():
    assert await spectaculum.SpectaculumAdapter().crawl(FakeClient({})) == []  # type: ignore[arg-type]
