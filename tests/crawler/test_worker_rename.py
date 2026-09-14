# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for re-crawls that correct a market name's whitespace."""

from datetime import date

from sqlmodel import Session, select

from ritterradar.crawler.base_adapter import MarketData
from ritterradar.crawler.worker import _upsert_market
from ritterradar.models.market import Market


def _market(name: str, source_url: str = "https://pfalzi.example/meile") -> MarketData:
    return MarketData(
        name=name,
        start_date=date(2031, 9, 5),
        end_date=date(2031, 9, 6),
        postal_code="76593",
        city="Gernsbach",
        source_url=source_url,
    )


def test_recrawl_with_corrected_spacing_updates_instead_of_duplicating(session: Session):
    assert _upsert_market(_market("MittelaltermeileAltstadtfest"), 48.76, 8.34, False, "P") == (
        1,
        0,
    )

    assert _upsert_market(_market("Mittelaltermeile Altstadtfest"), 48.76, 8.34, False, "P") == (
        0,
        1,
    )

    rows = session.exec(
        select(Market).where(Market.source_url == "https://pfalzi.example/meile")
    ).all()
    assert len(rows) == 1
    session.refresh(rows[0])
    assert rows[0].name == "Mittelaltermeile Altstadtfest"


def test_different_names_from_the_same_source_stay_separate(session: Session):
    url = "https://pfalzi.example/two-events"
    assert _upsert_market(_market("Burgfest", url), None, None, False, "P") == (1, 0)
    assert _upsert_market(_market("Burgfest Nacht", url), None, None, False, "P") == (1, 0)
    assert len(session.exec(select(Market).where(Market.source_url == url)).all()) == 2
