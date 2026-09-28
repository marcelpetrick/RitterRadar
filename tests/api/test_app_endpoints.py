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


def test_local_api_reference_is_served_without_external_assets(client: TestClient):
    for path in ("/api/docs", "/api/redoc"):
        response = client.get(path)
        assert response.status_code == 200
        assert "openapi" in response.text
        assert "https://" not in response.text


def test_readiness_reports_worker_and_database_state(client: TestClient, monkeypatch):
    from types import SimpleNamespace

    client.app.state.crawl_queue = SimpleNamespace(
        _workers=[SimpleNamespace(_task=SimpleNamespace(done=lambda: False))]
    )
    assert client.get("/ready").json() == {"ready": True}
    client.app.state.crawl_queue = None
    assert client.get("/ready").status_code == 503

    monkeypatch.setattr("ritterradar.main.get_engine", lambda: (_ for _ in ()).throw(OSError()))
    assert client.get("/ready").json() == {"ready": False}


def test_configure_logging_adds_private_file_handler(tmp_path, monkeypatch):
    import logging

    import ritterradar.main as main
    from ritterradar.config import Settings

    root_logger = logging.getLogger()
    original_root_level = root_logger.level
    access_logger = logging.getLogger("uvicorn.access")
    original_access_filters = access_logger.filters[:]
    noisy_loggers = ("httpx", "httpcore", "geopy", "urllib3")
    original_noisy_levels = {name: logging.getLogger(name).level for name in noisy_loggers}
    log_path = tmp_path / "state" / "ritterradar.log"
    log_path.parent.mkdir()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: Settings(_env_file=None, db_path=tmp_path / "state" / "app.db"),
    )
    # Keep pytest's capture handler intact while exercising the real file handler.
    monkeypatch.setattr(main.logging, "basicConfig", lambda **_kwargs: None)
    try:
        main._configure_logging()
        handler = next(
            handler
            for handler in root_logger.handlers
            if isinstance(handler, logging.handlers.RotatingFileHandler)
            and handler.baseFilename == str(log_path)
        )
        root_logger.setLevel(logging.INFO)
        logging.getLogger("ritterradar.test").info("private-log-test")
        handler.flush()

        assert log_path.is_file()
        assert log_path.stat().st_mode & 0o777 == 0o600
        assert "private-log-test" in log_path.read_text(encoding="utf-8")
    finally:
        for handler in root_logger.handlers[:]:
            if isinstance(
                handler, logging.handlers.RotatingFileHandler
            ) and handler.baseFilename == str(log_path):
                root_logger.removeHandler(handler)
                handler.close()
        root_logger.setLevel(original_root_level)
        access_logger.filters[:] = original_access_filters
        for name, level in original_noisy_levels.items():
            logging.getLogger(name).setLevel(level)


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


def test_crawl_endpoints_use_initialized_queue(client: TestClient, monkeypatch):
    class Queue:
        def get_status(self):
            return {"workers": 1, "queue_size": 2}

        def enqueue_all(self):
            return 3

    monkeypatch.setattr(client.app.state, "crawl_queue", Queue())  # type: ignore[attr-defined]
    assert client.get("/api/crawl/status").json() == {"workers": 1, "queue_size": 2}
    assert client.post("/api/crawl/trigger").json() == {
        "enqueued": 3,
        "message": "Enqueued 3 crawl jobs",
    }


def test_geocode_endpoint_found_and_not_found(client: TestClient, monkeypatch):
    async def fake_geocode(query: str, user_agent: str) -> GeoResult | None:
        return (
            GeoResult(48.14, 11.58, "München, Deutschland", False) if query == "München" else None
        )

    monkeypatch.setattr("ritterradar.api.settings.geocode", fake_geocode)

    assert client.post("/api/settings/geocode", json={"q": "München"}).json() == {
        "found": True,
        "query": "München",
        "latitude": 48.14,
        "longitude": 11.58,
        "display_name": "München, Deutschland",
        "uncertain": False,
    }
    assert client.post("/api/settings/geocode", json={"q": "Nirgendwo"}).json() == {
        "found": False,
        "query": "Nirgendwo",
    }


def test_update_settings_month_offsets_and_longitude(client: TestClient):
    response = client.put(
        "/api/settings",
        json={
            "home_latitude": 48.0,
            "home_longitude": 9.99,
            "default_month_offset_start": 1,
            "default_month_offset_end": 6,
        },
    )
    data = response.json()
    assert data["home_longitude"] == pytest.approx(9.99)
    assert (data["default_month_offset_start"], data["default_month_offset_end"]) == (1, 6)
    client.put("/api/settings", json={"home_latitude": None, "home_longitude": None})


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
