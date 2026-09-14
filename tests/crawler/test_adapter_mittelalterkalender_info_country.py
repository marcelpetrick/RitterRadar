# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for country detection in mittelalterkalender.info rows."""

import pytest
from bs4 import BeautifulSoup, Tag

from ritterradar.crawler.adapters.mittelalterkalender_info import _parse_row


def _row(postal_code: str, city: str, country_comment: str) -> Tag:
    html = f"""<table><tr class="isbfilter">
      <td class="nofloat">05.01.2026 <span class="dash"> bis </span></td>
      <td class="nofloat">06.01.2026</td>
      <td><button formaction="/mittelaltertermine/x.php">Raunacht</button></td>
      <td class="nofloat">{postal_code}</td><!-- PLZ -->
      <td class="nofloat">{city}</td><!-- Ort -->
      <!-- <td>, </td>-->
      {country_comment}
      <td></td></tr></table>"""
    row = BeautifulSoup(html, "lxml").find("tr")
    assert isinstance(row, Tag)
    return row


@pytest.mark.parametrize(
    ("postal_code", "city", "comment", "country"),
    [
        ("5710", "Kaprun", "<!-- <td>Österreich, </td> -->", "AT"),
        ("9630", "Wattwil", "<!-- <td>Schweiz, </td> -->", "CH"),
        ("7251 AZ", "Vorden", "<!-- <td>Niederlande, </td> -->", "NL"),
        ("524 31", "Herrljunga", "<!-- <td>Schweden, </td> -->", "SE"),
        ("01067", "Dresden", "<!-- <td>Deutschland, </td> -->", "DE"),
        ("01067", "Dresden", "", "DE"),
        ("01067", "Dresden", "<!-- <td>Atlantis, </td> -->", "DE"),
    ],
)
def test_country_comes_from_commented_out_cell(postal_code, city, comment, country):
    market = _parse_row(_row(postal_code, city, comment))
    assert market is not None
    assert (market.postal_code, market.city, market.country) == (postal_code, city, country)
