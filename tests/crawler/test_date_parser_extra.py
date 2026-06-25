# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Additional edge-case tests for date_parser."""

from datetime import date

from ritterradar.crawler.date_parser import parse_date_range


def test_range_spanning_months():
    result = parse_date_range("30. Juli bis 2. August 2026")
    assert result == (date(2026, 7, 30), date(2026, 8, 2))


def test_numeric_range_with_dash():
    result = parse_date_range("30.07.-02.08.2026")
    assert result == (date(2026, 7, 30), date(2026, 8, 2))


def test_single_day_numeric():
    assert parse_date_range("01.05.2027") == (date(2027, 5, 1), date(2027, 5, 1))


def test_returns_none_for_future_nonsense():
    assert parse_date_range("99.13.2026") is None


def test_parse_with_surrounding_whitespace():
    result = parse_date_range("   12. Juli 2026   ")
    assert result == (date(2026, 7, 12), date(2026, 7, 12))
