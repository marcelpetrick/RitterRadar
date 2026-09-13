# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for app-level routes, crawl API edge cases and the geocode endpoint."""

import pytest
from fastapi.testclient import TestClient

from ritterradar.geocoding.nominatim import GeoResult


def test_index_page_renders(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "RitterRadar" in response.text


def test_static_files_disable_caching(client: TestClient):
    response = client.get("/static/css/ritterradar.css")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache, max-age=0, must-revalidate"


def test_geo_progress_counts_add_up(client: TestClient):
    data = client.get("/api/crawl/geo-progress").json()
    assert data["total"] == data["geocoded"] + data["pending"]


def test_crawl_endpoints_without_initialised_queue(client: TestClient, monkeypatch):
    monkeypatch.setattr(client.app.state, "crawl_queue", None)  # type: ignore[attr-defined]
    assert client.get("/api/crawl/status").json() == {"error": "crawler not initialised"}
    assert client.post("/api/crawl/trigger").json() == {
        "error": "crawler not initialised",
        "enqueued": 0,
    }


def test_geocode_endpoint_found_and_not_found(client: TestClient, monkeypatch):
    async def fake_geocode(query: str, user_agent: str) -> GeoResult | None:
        return (
            GeoResult(48.14, 11.58, "München, Deutschland", False) if query == "München" else None
        )

    monkeypatch.setattr("ritterradar.api.settings.geocode", fake_geocode)

    assert client.get("/api/settings/geocode", params={"q": "München"}).json() == {
        "found": True,
        "query": "München",
        "latitude": 48.14,
        "longitude": 11.58,
        "display_name": "München, Deutschland",
        "uncertain": False,
    }
    assert client.get("/api/settings/geocode", params={"q": "Nirgendwo"}).json() == {
        "found": False,
        "query": "Nirgendwo",
    }


def test_update_settings_month_offsets_and_longitude(client: TestClient):
    response = client.put(
        "/api/settings",
        json={
            "home_longitude": 9.99,
            "default_month_offset_start": 1,
            "default_month_offset_end": 6,
        },
    )
    data = response.json()
    assert data["home_longitude"] == pytest.approx(9.99)
    assert (data["default_month_offset_start"], data["default_month_offset_end"]) == (1, 6)


def test_run_starts_uvicorn_with_configured_app(monkeypatch):
    import uvicorn

    from ritterradar.main import run

    calls: dict[str, object] = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: calls.update(app=app, **kwargs))
    run()
    assert calls["app"] == "ritterradar.main:app"
    assert {"host", "port", "log_level"} <= calls.keys()


def test_get_engine_creates_database_directory(tmp_path, monkeypatch):
    import ritterradar.database.engine as engine_mod
    from ritterradar.config import Settings

    db_path = tmp_path / "nested" / "ritterradar.db"
    monkeypatch.setattr(engine_mod, "_engine", None)
    monkeypatch.setattr(engine_mod, "get_settings", lambda: Settings(db_path=db_path))

    engine = engine_mod.get_engine()
    try:
        assert db_path.parent.is_dir()
        assert str(engine.url).endswith("ritterradar.db")
        assert engine_mod.get_engine() is engine
    finally:
        engine.dispose()
