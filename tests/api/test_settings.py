# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for the settings API."""

from fastapi.testclient import TestClient


def test_get_settings_default(client: TestClient):
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["default_radius_km"] == 100.0
    assert data["home_latitude"] is None


def test_update_settings(client: TestClient):
    r = client.put("/api/settings", json={
        "home_latitude": 48.1351,
        "home_longitude": 11.5820,
        "home_label": "München",
        "default_radius_km": 75.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["home_latitude"] == pytest.approx(48.1351)
    assert data["home_label"] == "München"
    assert data["default_radius_km"] == pytest.approx(75.0)


def test_update_settings_partial(client: TestClient):
    client.put("/api/settings", json={"default_radius_km": 200.0})
    r = client.get("/api/settings")
    assert r.json()["default_radius_km"] == pytest.approx(200.0)


import pytest
