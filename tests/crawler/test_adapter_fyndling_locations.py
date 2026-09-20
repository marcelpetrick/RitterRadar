# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for fyndling.de location cleanup (cantons, legacy markers, postcode order)."""

import pytest

from ritterradar.crawler.adapters.fyndling import _parse_location


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        ("Zofingen AG (🇨🇭CH)", (None, "Zofingen", "CH")),
        ("3177 Laupen BE (🇨🇭CH)", ("3177", "Laupen", "CH")),
        ("Eschenbach LU (🇨🇭CH)", (None, "Eschenbach", "CH")),
        ("Neues OK (🇨🇭CH)", (None, None, "CH")),
        ("Schloss Lenzburg Lenzburg AG (🇨🇭CH)", (None, "Lenzburg", "CH")),
        ("Störmede (wo immer das auch sein mag)", (None, "Störmede", "DE")),
        ("0xxxx", (None, None, "DE")),
        ("39040 Campo di Trens (I)", ("39040", "Campo di Trens", "IT")),
        ("D.87700 Memmingen", ("87700", "Memmingen", "DE")),
        ("Drage 21423", ("21423", "Drage", "DE")),
        ("Lachen SZ", (None, "Lachen SZ", "DE")),
    ],
)
def test_location_cleanup(cell, expected):
    assert _parse_location(cell) == expected
