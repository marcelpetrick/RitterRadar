# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for the crawl status and trigger API endpoints."""

from fastapi.testclient import TestClient


def test_crawl_status(client: TestClient):
    r = client.get("/api/crawl/status")
    assert r.status_code == 200
    data = r.json()
    # Either the crawler is initialised or it returns an error key
    assert "error" in data or "pending" in data


def test_crawl_trigger(client: TestClient):
    r = client.post("/api/crawl/trigger")
    assert r.status_code == 200
    data = r.json()
    assert "enqueued" in data or "error" in data


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_sources_list(client: TestClient):
    r = client.get("/api/sources")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
