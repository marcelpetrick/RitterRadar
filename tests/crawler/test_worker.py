# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for crawler worker persistence behavior."""

from datetime import date

from sqlmodel import Session, select

from ritterradar.crawler.base_adapter import MarketData
from ritterradar.crawler.worker import _upsert_market
from ritterradar.models.market import Market


def test_upsert_repairs_uncertain_coordinates(session: Session):
    market_data = MarketData(
        name="Coordinate repair test",
        start_date=date(2030, 1, 1),
        end_date=date(2030, 1, 2),
        city="Schöneberg",
        postal_code="55444",
        source_url="https://example.com/coordinate-repair",
    )
    _upsert_market(market_data, 52.482157, 13.3551901, True, "Test")

    inserted, updated = _upsert_market(market_data, 49.88, 7.75, False, "Test")

    market = session.exec(select(Market).where(Market.source_url == market_data.source_url)).one()
    session.refresh(market)
    assert (inserted, updated) == (0, 1)
    assert market.latitude == 49.88
    assert market.longitude == 7.75
    assert market.geocode_uncertain is False
