# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Offline fixture tests for the disabled heuristic adapters and generic_table.

Their sites are offline (see documents/03_sources.md), but the adapters stay
registered and must keep working if a source is re-enabled or reused.
"""

from datetime import date

from ritterradar.crawler.adapters import (
    generic_table,
    mittelalterfeste,
    mittelaltermarkt,
    ritterschaft,
    schwerttanz,
)
from tests.crawler.fake_client import FakeClient

Y = date.today().year


# ── mittelalterfeste.de ─────────────────────────────────────────────────

_MF_URL = mittelalterfeste.MittelalterfestAdapter.BASE_URL


async def test_mittelalterfeste_parses_event_articles():
    page = f"""
      <article class="event"><h3>Ritterturnier zu Kaltenberg</h3><p>12. bis 14. Juli {Y}</p>
        <span class="ort">82269 Geltendorf</span><a href="/termine/kaltenberg">Mehr</a></article>
      <article class="event"><h3>Wikingerfest am Hafen</h3><p>Termin: 01.08.{Y}</p>
        <p>Treffpunkt 24837 am Hafen</p></article>
      <article class="event"><p>ohne Überschrift 01.08.{Y}</p></article>
      <article class="event"><h3>Ohne Datum</h3><p>bald</p></article>
      <article class="event"><h3>AB</h3></article>
    """
    client = FakeClient({_MF_URL: page})
    results = await mittelalterfeste.MittelalterfestAdapter().crawl(client)  # type: ignore[arg-type]

    assert [r.name for r in results] == ["Ritterturnier zu Kaltenberg", "Wikingerfest am Hafen"]
    turnier, wikinger = results
    assert (turnier.start_date, turnier.end_date) == (date(Y, 7, 12), date(Y, 7, 14))
    assert (turnier.postal_code, turnier.city) == ("82269", "Geltendorf")
    assert turnier.source_url == f"{mittelalterfeste.BASE}/termine/kaltenberg"
    assert (wikinger.postal_code, wikinger.city, wikinger.market_type) == ("24837", None, "viking")
    assert client.requested == [_MF_URL, f"{_MF_URL}?seite=2"]


async def test_mittelalterfeste_falls_back_to_cards_and_handles_failures():
    cards = f'<div class="card"><h3>Burgfest im Advent</h3><span>05.12.{Y}</span></div>'
    results = await mittelalterfeste.MittelalterfestAdapter().crawl(FakeClient({_MF_URL: cards}))  # type: ignore[arg-type]
    assert [(r.name, r.market_type) for r in results] == [("Burgfest im Advent", "christmas")]

    empty = FakeClient({_MF_URL: "<p>Keine Termine</p>"})
    assert await mittelalterfeste.MittelalterfestAdapter().crawl(empty) == []  # type: ignore[arg-type]
    failing = FakeClient({_MF_URL: RuntimeError("TLS error")})
    assert await mittelalterfeste.MittelalterfestAdapter().crawl(failing) == []  # type: ignore[arg-type]


def test_mittelalterfeste_type_detection():
    assert mittelalterfeste._detect_type("Historisches Stadtfest") == "renaissance"
    assert mittelalterfeste._detect_type("Magie und Drachen") == "fantasy"
    assert mittelalterfeste._detect_type("Burgfest") == "medieval"


# ── mittelaltermarkt.com ────────────────────────────────────────────────

_MM_URL = mittelaltermarkt.MittelaltermarktAdapter.BASE_URL


async def test_mittelaltermarkt_parses_items_until_gone_page():
    page = f"""
      <div class="termin"><h3>Burgfest Stolpen</h3><p>05.09.{Y} - 06.09.{Y}, 01833 Stolpen</p>
        <a href="/burgfest-stolpen">zum eintrag</a></div>
      <div class="eintrag"><p>Weihnachtsmarkt ohne Überschrift 12.12.{Y}</p></div>
      <div class="post">kurz</div>
      <div class="entry"><h2>Fantasy-Zauber</h2><p>kein Datum bekannt</p></div>
      <div class="event"><h4>Adventszauber</h4><p>12.12.{Y}</p></div>
    """
    client = FakeClient({_MM_URL: page, f"{_MM_URL}/page/2": ("", 410)})
    results = await mittelaltermarkt.MittelaltermarktAdapter().crawl(client)  # type: ignore[arg-type]

    assert [(r.name, r.market_type) for r in results] == [
        ("Burgfest Stolpen", "medieval"),
        ("Adventszauber", "christmas"),
    ]
    assert (results[0].postal_code, results[0].city) == ("01833", "Stolpen")
    assert results[0].source_url == f"{mittelaltermarkt.BASE}/burgfest-stolpen"
    assert results[1].source_url == mittelaltermarkt.BASE


async def test_mittelaltermarkt_empty_and_failing_pages():
    empty = FakeClient({_MM_URL: "<html><title>Domain zu verkaufen</title><p>x</p></html>"})
    assert await mittelaltermarkt.MittelaltermarktAdapter().crawl(empty) == []  # type: ignore[arg-type]
    failing = FakeClient({_MM_URL: ("", 500)})
    assert await mittelaltermarkt.MittelaltermarktAdapter().crawl(failing) == []  # type: ignore[arg-type]


def test_mittelaltermarkt_type_detection():
    assert mittelaltermarkt._detect_type("Renaissance") == "renaissance"
    assert mittelaltermarkt._detect_type("Wikinger") == "viking"
    assert mittelaltermarkt._detect_type("Drachenfest") == "fantasy"


# ── schwerttanz.de ──────────────────────────────────────────────────────

_ST_URL = schwerttanz.SchwerttanzAdapter.BASE_URL


async def test_schwerttanz_parses_table_rows():
    page = f"""
      <table>
        <tr><td><strong>Markt zu Tittmoning</strong></td><td>01.08.{Y}</td>
            <td>84529 Tittmoning</td><td><a href="/markt/tittmoning">mehr</a></td></tr>
        <tr><td>02.09.{Y}</td><td>Herbstmarkt, Altötting</td></tr>
        <tr><td>x</td></tr>
        <tr><td>Kein Termin vorhanden</td></tr>
      </table>
    """
    client = FakeClient({_ST_URL: page})
    results = await schwerttanz.SchwerttanzAdapter().crawl(client)  # type: ignore[arg-type]

    assert [r.name for r in results] == ["Markt zu Tittmoning", "Altötting"]
    assert (results[0].postal_code, results[0].city) == ("84529", "Tittmoning")
    assert results[0].source_url == f"{schwerttanz.BASE}/markt/tittmoning"
    assert results[1].source_url == schwerttanz.BASE


async def test_schwerttanz_returns_empty_list_on_fetch_error():
    assert await schwerttanz.SchwerttanzAdapter().crawl(FakeClient({})) == []  # type: ignore[arg-type]


# ── ritterschaft.de ─────────────────────────────────────────────────────

_RS_URL = ritterschaft.RitterschaftAdapter.BASE_URL


async def test_ritterschaft_parses_termin_items():
    page = f"""
      <div class="termin"><h3>Ritterspiele Ehrenberg</h3><p>20.06.{Y}, 87629 Füssen</p>
        <a href="/termine/ehrenberg">mehr</a></div>
      <div class="termin"><strong>21.06.{Y}</strong><span>Lagerleben am Burgberg</span></div>
      <div class="termin">kurz</div>
      <div class="termin"><h3>Ohne Datum</h3><p>wird noch bekannt gegeben</p></div>
    """
    client = FakeClient({_RS_URL: page})
    results = await ritterschaft.RitterschaftAdapter().crawl(client)  # type: ignore[arg-type]

    # A heading that is only a date falls back to the first longer words of the item.
    assert [r.name for r in results] == ["Ritterspiele Ehrenberg", f"21.06.{Y} Lagerleben Burgberg"]
    assert (results[0].postal_code, results[0].city) == ("87629", "Füssen")
    assert results[0].source_url == f"{ritterschaft.BASE}/termine/ehrenberg"


async def test_ritterschaft_falls_back_to_articles_and_handles_errors():
    page = f"<article><h2>Turnier am Lech</h2><p>05.05.{Y}</p></article>"
    results = await ritterschaft.RitterschaftAdapter().crawl(FakeClient({_RS_URL: page}))  # type: ignore[arg-type]
    assert [r.name for r in results] == ["Turnier am Lech"]
    assert await ritterschaft.RitterschaftAdapter().crawl(FakeClient({})) == []  # type: ignore[arg-type]


# ── generic_table ───────────────────────────────────────────────────────


async def test_generic_table_extracts_rows_from_tables():
    url = "https://kalender.example/termine"
    page = f"""
      <table>
        <tr><th>Datum</th><th>Name</th><th>Ort</th></tr>
        <tr><td>12.07.{Y} - 14.07.{Y}</td><td>Burgfest</td><td>84489 Burghausen</td></tr>
        <tr><td>01.08.{Y}</td><td>Sommermarkt</td><td>Treffpunkt 84529</td></tr>
        <tr><td>nur eine Zelle</td></tr>
        <tr><td>Name ohne Datum</td><td>Ort</td></tr>
      </table>
    """
    adapter = generic_table.GenericTableAdapter(url=url, source_name="Beispielkalender")
    results = await adapter.crawl(FakeClient({url: page}))  # type: ignore[arg-type]

    assert [(r.name, r.postal_code, r.city) for r in results] == [
        ("Burgfest", "84489", "Burghausen"),
        ("Sommermarkt", "84529", None),
    ]
    assert results[0].end_date == date(Y, 7, 14)
    assert all(r.source_url == url and r.confidence_score == 0.6 for r in results)


async def test_generic_table_without_url_or_on_error_returns_nothing():
    assert await generic_table.GenericTableAdapter().crawl(FakeClient({})) == []  # type: ignore[arg-type]
    adapter = generic_table.GenericTableAdapter(url="https://down.example/")
    assert await adapter.crawl(FakeClient({})) == []  # type: ignore[arg-type]
