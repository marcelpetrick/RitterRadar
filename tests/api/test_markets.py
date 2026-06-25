# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Integration tests for the markets API."""

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from ritterradar.models.market import Market


def _make_market(session: Session, **kwargs) -> Market:
    defaults = dict(
        name="TestMarkt",
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 12),
        source_url="https://example.com/1",
        source_name="Test",
        latitude=48.1351,
        longitude=11.5820,
        city="München",
        postal_code="80331",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    m = Market(**defaults)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def test_list_markets_empty(client: TestClient):
    r = client.get("/api/markets")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_markets_returns_market(client: TestClient, session: Session):
    _make_market(session, name="Markt A", source_url="https://example.com/a")
    r = client.get("/api/markets")
    assert r.status_code == 200
    names = [m["name"] for m in r.json()]
    assert "Markt A" in names


def test_list_markets_date_filter(client: TestClient, session: Session):
    _make_market(session, name="July", start_date=date(2026, 7, 1), source_url="https://example.com/jul")
    _make_market(session, name="Dec", start_date=date(2026, 12, 1), source_url="https://example.com/dec")
    r = client.get("/api/markets?date_from=2026-07-01&date_to=2026-07-31")
    assert r.status_code == 200
    names = [m["name"] for m in r.json()]
    assert "July" in names
    assert "Dec" not in names


def test_list_markets_radius_filter(client: TestClient, session: Session):
    # Munich (~48.1, 11.6) — within 50 km of itself
    _make_market(session, name="Near", latitude=48.15, longitude=11.60,
                 source_url="https://example.com/near")
    # Hamburg (far away from Munich)
    _make_market(session, name="Far", latitude=53.57, longitude=10.02,
                 source_url="https://example.com/far")
    r = client.get("/api/markets?lat=48.1351&lon=11.5820&radius_km=50")
    assert r.status_code == 200
    names = [m["name"] for m in r.json()]
    assert "Near" in names
    assert "Far" not in names


def test_hide_market(client: TestClient, session: Session):
    m = _make_market(session, name="ToHide", source_url="https://example.com/hide")
    r = client.post(f"/api/markets/{m.id}/hide")
    assert r.status_code == 200
    assert r.json()["hidden"] is True

    # Hidden should not appear in default listing
    r2 = client.get("/api/markets")
    ids = [x["id"] for x in r2.json()]
    assert m.id not in ids

    # But appears when include_hidden=true
    r3 = client.get("/api/markets?include_hidden=true")
    ids3 = [x["id"] for x in r3.json()]
    assert m.id in ids3


def test_hide_market_not_found(client: TestClient):
    r = client.post("/api/markets/99999/hide")
    assert r.status_code == 404


def test_market_type_filter(client: TestClient, session: Session):
    _make_market(session, name="Med", market_type="medieval",
                 source_url="https://example.com/med")
    _make_market(session, name="Vik", market_type="viking",
                 source_url="https://example.com/vik")
    r = client.get("/api/markets?market_type=viking")
    assert r.status_code == 200
    types = {m["market_type"] for m in r.json()}
    assert types <= {"viking"}
