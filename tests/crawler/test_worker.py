# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for crawler worker persistence behavior."""

from datetime import date

from sqlmodel import Session, select

from ritterradar.crawler.base_adapter import MarketData
from ritterradar.crawler.worker import _get_trusted_coordinates, _upsert_market
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


def test_trusted_coordinates_skip_revalidation():
    trusted = MarketData(
        name="Trusted coordinate test",
        start_date=date(2030, 2, 1),
        end_date=date(2030, 2, 2),
        city="Potsdam",
        postal_code="14467",
        source_url="https://example.com/trusted-coordinate",
    )
    uncertain = MarketData(
        name="Uncertain coordinate test",
        start_date=date(2030, 3, 1),
        end_date=date(2030, 3, 2),
        city="Schöneberg",
        postal_code="55444",
        source_url="https://example.com/uncertain-coordinate",
    )
    _upsert_market(trusted, 52.4009, 13.0591, False, "Test")
    _upsert_market(uncertain, 52.4821, 13.3551, True, "Test")

    assert _get_trusted_coordinates(trusted) == (52.4009, 13.0591)
    assert _get_trusted_coordinates(uncertain) is None
