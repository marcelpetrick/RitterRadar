# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for the mittelalterkalender.info adapter (offline HTML fixtures)."""

from datetime import date

from ritterradar.crawler.adapters.mittelalterkalender_info import (
    _HOME,
    BASE,
    MittelalterkalenderInfoAdapter,
    _discover_list_urls,
    _fallback_urls,
)
from tests.crawler.fake_client import FakeClient

_THIS = date.today().year
_NEXT = _THIS + 1


def _list_page(name: str, year: int) -> str:
    return f"""<table><tr class="isbfilter">
      <td>01.05.{year}<span class="dash"> bis </span></td><td>02.05.{year}</td>
      <td><button formaction="/mittelaltertermine/x.php">{name}</button></td>
      <td>65510</td><td>Idstein</td><td></td></tr></table>"""


def test_discover_list_urls_handles_renamed_pages():
    renamed = "historische-feste-mittelaltermaerkte-und-fantasy-festivals"
    home = f"""
      <a href="{BASE}/mittelaltermarkt/mittelalterfeste-{_THIS}-nach-datum.php">A</a>
      <a href="/mittelaltermarkt/{renamed}-{_NEXT}-nach-datum.php">B</a>
      <a href="{BASE}/mittelaltermarkt/nach-datum/monat-april-{_NEXT}.php">monthly</a>
    """
    assert _discover_list_urls(home) == {
        _THIS: f"{BASE}/mittelaltermarkt/mittelalterfeste-{_THIS}-nach-datum.php",
        _NEXT: f"{BASE}/mittelaltermarkt/{renamed}-{_NEXT}-nach-datum.php",
    }


async def test_crawl_uses_discovered_urls():
    this_url = f"{BASE}/mittelaltermarkt/mittelalterfeste-{_THIS}-nach-datum.php"
    next_url = f"{BASE}/mittelaltermarkt/historische-feste-x-{_NEXT}-nach-datum.php"
    client = FakeClient(
        {
            _HOME: f'<a href="{this_url}">a</a><a href="{next_url}">b</a>',
            this_url: _list_page("Hexenmarkt", _THIS),
            next_url: _list_page("Sturmwacht", _NEXT),
        }
    )
    results = await MittelalterkalenderInfoAdapter().crawl(client)  # type: ignore[arg-type]
    assert [r.name for r in results] == ["Hexenmarkt", "Sturmwacht"]
    assert client.requested == [_HOME, this_url, next_url]


async def test_crawl_falls_back_to_known_patterns_without_homepage():
    new_style, old_style = _fallback_urls(_THIS)
    client = FakeClient({old_style: _list_page("Ritterfest", _THIS)})
    results = await MittelalterkalenderInfoAdapter().crawl(client)  # type: ignore[arg-type]
    assert [r.name for r in results] == ["Ritterfest"]
    assert client.requested[:3] == [_HOME, new_style, old_style]
