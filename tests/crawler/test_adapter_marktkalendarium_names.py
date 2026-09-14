# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for multi-line event names on Pfalzis Marktkalendarium."""

import pytest
from bs4 import BeautifulSoup, Tag

from ritterradar.crawler.adapters.marktkalendarium import _parse_row


def _row(name_cell: str) -> Tag:
    html = (
        "<table><tr><td>5.9.2026</td><td>6.9.2026</td>"
        f"<td>{name_cell}</td>"
        "<td><a href='https://maps.google.de/maps?q=D-76593 Gernsbach'>D-76593 Gernsbach</a></td>"
        "<td>Altstadt</td><td><a href='https://gernsbach.example/'>Web</a></td></tr></table>"
    )
    row = BeautifulSoup(html, "lxml").find("tr")
    assert isinstance(row, Tag)
    return row


@pytest.mark.parametrize(
    ("name_cell", "expected"),
    [
        ("Mittelaltermeile<br/>Altstadtfest ", "Mittelaltermeile Altstadtfest"),
        (
            "4. großer Mittelaltermarkt<br/> rund um die Bettinger ",
            "4. großer Mittelaltermarkt rund um die Bettinger",
        ),
        (
            "Spielkurs Passau - Workshop<br/> Drehleier  Dudelsack Bal Folk",
            "Spielkurs Passau - Workshop Drehleier Dudelsack Bal Folk",
        ),
        ("Burgfest", "Burgfest"),
    ],
)
def test_multi_line_names_keep_word_boundaries(name_cell, expected):
    market = _parse_row(_row(name_cell))
    assert market is not None
    assert market.name == expected
