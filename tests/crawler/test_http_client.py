# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for the polite HTTP client (retries, backoff, domain-drift guard)."""

from collections.abc import Callable

import httpx
import pytest

import ritterradar.crawler.http_client as http_client
from ritterradar.crawler.http_client import PoliteHttpClient, _domain_root, make_client

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch):
    monkeypatch.setattr(http_client, "_BACKOFF_MAX", 0.0)


def _polite(handler: Handler, **kwargs) -> tuple[httpx.AsyncClient, PoliteHttpClient]:
    raw = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return raw, PoliteHttpClient(raw, min_delay=0, max_delay=0, **kwargs)


def test_domain_root():
    assert _domain_root("www.sedo.com") == "sedo.com"
    assert _domain_root("SUB.Example.DE.") == "example.de"
    assert _domain_root("localhost") == "localhost"


async def test_get_sends_browser_user_agent():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["User-Agent"])
        return httpx.Response(200, text="ok")

    raw, client = _polite(handler)
    async with raw:
        response = await client.get("https://example.com/termine")
    assert response.text == "ok"
    assert seen == [http_client._USER_AGENT]


async def test_retries_rate_limited_response_then_succeeds():
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(429 if len(calls) == 1 else 200)

    raw, client = _polite(handler)
    async with raw:
        response = await client.get("https://example.com/")
    assert response.status_code == 200
    assert len(calls) == 2


async def test_returns_last_unavailable_response_when_retries_are_exhausted():
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503)

    raw, client = _polite(handler, max_retries=2)
    async with raw:
        response = await client.get("https://example.com/")
    assert response.status_code == 503
    assert len(calls) == 3


async def test_network_errors_raise_after_all_retries():
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ConnectError("connection refused", request=request)

    raw, client = _polite(handler, max_retries=2)
    async with raw:
        with pytest.raises(httpx.RequestError, match="retries exhausted"):
            await client.get("https://example.com/")
    assert len(calls) == 3


async def test_redirect_to_other_domain_is_rejected_as_domain_drift():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "old-market.de":
            return httpx.Response(302, headers={"Location": "https://www.sedo.com/parked"})
        return httpx.Response(200, text="domain for sale")

    raw, client = _polite(handler)
    async with raw:
        with pytest.raises(httpx.RequestError, match="Domain drift"):
            await client.get("https://old-market.de/termine")


async def test_make_client_defaults():
    client = make_client(verify=False)
    async with client:
        assert client.headers["User-Agent"] == http_client._USER_AGENT
        assert client.headers["Accept-Language"].startswith("de-DE")
        assert client.follow_redirects is True
