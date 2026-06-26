# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""German date string parser for market event listings."""

import re
from datetime import date

_DE_MONTHS: dict[str, int] = {
    "januar": 1,
    "jän": 1,
    "jan": 1,
    "februar": 2,
    "feb": 2,
    "märz": 3,
    "maerz": 3,
    "mär": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "mai": 5,
    "juni": 6,
    "jun": 6,
    "juli": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "oktober": 10,
    "okt": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "dezember": 12,
    "dez": 12,
    "dec": 12,
}

# Patterns ordered from most- to least-specific
_PATTERNS = [
    # "12. bis 14. Juli 2026" / "12. und 14. Juli 2026"
    re.compile(
        r"(\d{1,2})\.\s*(?:bis|und|-)\s*(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s+(\d{4})",
        re.IGNORECASE,
    ),
    # "12. Juli bis 14. August 2026"
    re.compile(
        r"(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s+(?:bis|und|-)\s+(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s+(\d{4})",
        re.IGNORECASE,
    ),
    # "12.07. - 14.07.2026" / "12.07.-14.07.2026"
    re.compile(
        r"(\d{1,2})\.(\d{1,2})\.\s*[-–]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})",
    ),
    # "12.07.2026 - 14.07.2026"
    re.compile(
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s*[-–]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})",
    ),
    # "12. Juli 2026" (single day)
    re.compile(
        r"(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s+(\d{4})",
        re.IGNORECASE,
    ),
    # "12.07.2026" (single day)
    re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})"),
]


def parse_date_range(text: str) -> tuple[date, date] | None:
    """Extract a (start_date, end_date) pair from a German date string.

    Returns ``None`` when no recognisable date pattern is found.
    """
    text = text.strip()

    # Pattern: "12. bis 14. Juli 2026"
    m = _PATTERNS[0].search(text)
    if m:
        day1, day2, month_str, year = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
        month = _month(month_str)
        if month:
            start = _safe_date(year, month, day1)
            end = _safe_date(year, month, day2)
            if start and end:
                return start, end

    # Pattern: "12. Juli bis 14. August 2026"
    m = _PATTERNS[1].search(text)
    if m:
        day1, month1_str = int(m.group(1)), m.group(2)
        day2, month2_str, year = int(m.group(3)), m.group(4), int(m.group(5))
        month1 = _month(month1_str)
        month2 = _month(month2_str)
        if month1 and month2:
            start = _safe_date(year, month1, day1)
            end = _safe_date(year, month2, day2)
            if start and end:
                return start, end

    # Pattern: "12.07. - 14.07.2026"
    m = _PATTERNS[2].search(text)
    if m:
        day1, month1 = int(m.group(1)), int(m.group(2))
        day2, month2, year = int(m.group(3)), int(m.group(4)), int(m.group(5))
        start = _safe_date(year, month1, day1)
        end = _safe_date(year, month2, day2)
        if start and end:
            return start, end

    # Pattern: "12.07.2026 - 14.07.2026"
    m = _PATTERNS[3].search(text)
    if m:
        day1, month1, year1 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        day2, month2, year2 = int(m.group(4)), int(m.group(5)), int(m.group(6))
        start = _safe_date(year1, month1, day1)
        end = _safe_date(year2, month2, day2)
        if start and end:
            return start, end

    # Pattern: "12. Juli 2026" (single day)
    m = _PATTERNS[4].search(text)
    if m:
        day, month_str, year = int(m.group(1)), m.group(2), int(m.group(3))
        month = _month(month_str)
        if month:
            d = _safe_date(year, month, day)
            if d:
                return d, d

    # Pattern: "12.07.2026" (single day)
    m = _PATTERNS[5].search(text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        d = _safe_date(year, month, day)
        if d:
            return d, d

    return None


def _month(name: str) -> int | None:
    return _DE_MONTHS.get(name.lower())


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None
