# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for the German date string parser."""

from datetime import date

import pytest

from ritterradar.crawler.date_parser import parse_date_range


@pytest.mark.parametrize("text,expected", [
    # "12. bis 14. Juli 2026"
    ("12. bis 14. Juli 2026",      (date(2026, 7, 12), date(2026, 7, 14))),
    # "12. und 14. März 2026"
    ("12. und 14. März 2026",      (date(2026, 3, 12), date(2026, 3, 14))),
    # "12. Juli bis 14. August 2026"
    ("12. Juli bis 14. August 2026", (date(2026, 7, 12), date(2026, 8, 14))),
    # "12.07. - 14.07.2026"
    ("12.07. - 14.07.2026",        (date(2026, 7, 12), date(2026, 7, 14))),
    # "12.07.2026 - 14.07.2026"
    ("12.07.2026 - 14.07.2026",    (date(2026, 7, 12), date(2026, 7, 14))),
    # "12. Juli 2026" (single day)
    ("12. Juli 2026",              (date(2026, 7, 12), date(2026, 7, 12))),
    # "12.07.2026" (single day)
    ("12.07.2026",                 (date(2026, 7, 12), date(2026, 7, 12))),
    # With weekday prefix
    ("Fr, 15. August 2026",        (date(2026, 8, 15), date(2026, 8, 15))),
    # Lowercase month
    ("03. januar 2027",            (date(2027, 1, 3), date(2027, 1, 3))),
    # december
    ("24. bis 26. Dezember 2026",  (date(2026, 12, 24), date(2026, 12, 26))),
])
def test_parse_known_formats(text, expected):
    result = parse_date_range(text)
    assert result == expected, f"For {text!r}: expected {expected}, got {result}"


def test_parse_returns_none_for_garbage():
    assert parse_date_range("kein datum hier") is None
    assert parse_date_range("") is None
    assert parse_date_range("   ") is None


def test_parse_ignores_invalid_dates():
    # Day 32 is invalid
    assert parse_date_range("32.07.2026") is None


def test_parse_embedded_in_larger_text():
    text = "Mittelaltermarkt in Köln, 12. Juli bis 14. Juli 2026, Stadtpark"
    result = parse_date_range(text)
    assert result == (date(2026, 7, 12), date(2026, 7, 14))
