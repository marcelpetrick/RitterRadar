# SPDX-License-Identifier: GPL-3.0-or-later
"""Adversarial regressions use isolated storage and never contact live services."""

import asyncio
import base64
import logging
import socket
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import httpcore
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from ritterradar.api.settings import router as settings_router
from ritterradar.config import Settings
from ritterradar.crawler.base_adapter import MarketData, validate_market
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.network import PublicNetworkBackend
from ritterradar.crawler.queue import CrawlQueue
from ritterradar.geocoding.transport import SafeGeocoderAdapter
from ritterradar.models.crawl_job import CrawlJob
from ritterradar.models.source import Source
from ritterradar.runtime import InstanceLock
from ritterradar.security import PrivateAccessLog, SecurityMiddleware, safe_web_url


@pytest.fixture
def secure_app(monkeypatch):
    settings = Settings(_env_file=None, allowed_hosts=["localhost"], workers=0, request_limit=10000)
    monkeypatch.setattr("ritterradar.security.get_settings", lambda: settings)
    monkeypatch.setattr("ritterradar.api.settings.get_settings", lambda: settings)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr("ritterradar.database.engine._engine", engine)
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    app.include_router(settings_router)

    @app.api_route("/probe", methods=["GET", "POST"])
    async def probe():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"ok": True}

    yield app, settings
    engine.dispose()


def browser(app, peer="127.0.0.1"):
    return TestClient(
        app,
        base_url="http://localhost",
        client=(peer, 1234),
        headers={"X-RitterRadar-Request": "1"},
    )


@pytest.mark.parametrize(
    "host",
    [
        "attacker.example",
        "localhost@evil.example",
        "localhost/path",
        "localhost:bad",
        "localhost\\evil",
        "localhost?x=1",
    ],
)
def test_untrusted_authorities_never_reach_api(secure_app, host):
    assert browser(secure_app[0]).get("/probe", headers={"Host": host}).status_code == 400


def test_origin_metadata_and_custom_header_are_enforced(secure_app):
    c = browser(secure_app[0])
    assert c.post("/probe", headers={"Origin": "http://evil.example"}).status_code == 403
    assert c.post("/probe", headers={"Origin": "null"}).status_code == 403
    assert c.post("/probe", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert c.post("/probe", headers={"X-RitterRadar-Request": ""}).status_code == 403
    assert c.post("/probe", headers={"Origin": "http://localhost"}).status_code == 200
    assert c.post("/probe").status_code == 200  # Explicit CLI header, no browser origin.


def test_network_clients_require_authentication(secure_app):
    app, settings = secure_app
    c = browser(app, "192.0.2.1")
    assert c.get("/probe").status_code == 403
    assert c.get("/health").status_code == 200
    secret = "test-only-random-secret-with-32-characters"
    settings.auth_token = SecretStr(secret)
    assert c.get("/probe").status_code == 401
    assert c.get("/probe", headers={"Authorization": "Basic !!!"}).status_code == 401
    assert c.get("/probe", headers={"Authorization": "Bearer incorrect"}).status_code == 401
    assert c.get("/probe", headers={"Authorization": f"Bearer {secret}"}).status_code == 200
    encoded = base64.b64encode(f"ritterradar:{secret}".encode()).decode()
    assert c.get("/probe", headers={"Authorization": f"Basic {encoded}"}).status_code == 200


def test_bad_credentials_are_throttled_without_blocking_valid_token(secure_app):
    app, settings = secure_app
    secret = "a" * 32
    settings.auth_token = SecretStr(secret)
    c = browser(app, "192.0.2.1")
    assert [
        c.get("/probe", headers={"Authorization": "Bearer wrong"}).status_code for _ in range(10)
    ] == [401] * 10
    assert c.get("/probe", headers={"Authorization": "Bearer wrong"}).status_code == 429
    assert c.get("/probe", headers={"Authorization": f"Bearer {secret}"}).status_code == 200


def test_short_auth_token_is_rejected_at_configuration_boundary():
    with pytest.raises(ValueError, match="at least 32"):
        Settings(_env_file=None, auth_token="short")


def test_request_budgets_and_headers(secure_app):
    app, settings = secure_app
    c = browser(app)
    assert c.post("/probe", content=b"x" * 16385).status_code == 413
    assert c.get("/probe?" + "q" * 4097).status_code == 414
    r = c.get("/probe")
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "https://tile.openstreetmap.org" in r.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    settings.offline = True
    assert "openstreetmap" not in c.get("/probe").headers["content-security-policy"]
    settings.request_limit = 10
    statuses = [c.get("/probe").status_code for _ in range(12)]
    assert 429 in statuses


@pytest.mark.parametrize(
    "payload",
    [
        {"home_latitude": 999, "home_longitude": 11},
        {"home_latitude": 48},
        {"default_radius_km": -1},
        {"default_month_offset_start": 8, "default_month_offset_end": 3},
        {"default_radius_km": None},
        {"home_label": "x" * 501},
        {"home_latitude": 48, "home_longitude": None},
    ],
)
def test_invalid_settings_are_rejected_without_mutation(secure_app, payload):
    c = browser(secure_app[0])
    before = c.get("/api/settings").json()
    assert c.put("/api/settings", json=payload).status_code == 422
    assert c.get("/api/settings").json() == before


def test_clear_home_and_offline_geocoder(secure_app):
    app, settings = secure_app
    c = browser(app)
    assert (
        c.put(
            "/api/settings", json={"home_latitude": 0, "home_longitude": 0, "home_label": "private"}
        ).status_code
        == 200
    )
    assert c.delete("/api/settings/history").json() == {"cleared": True}
    assert c.get("/api/settings").json()["home_label"] is None
    assert c.post("/api/settings/geocode", json={"q": "x" * 301}).status_code == 422
    settings.offline = True
    assert c.post("/api/settings/geocode", json={"q": "Berlin"}).status_code == 503
    assert c.get("/api/settings/geocode?q=private").status_code == 405


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,hi",
        "file:///tmp/a",
        "https://u:p@example.org",
        "https://example.org/\nx",
        "https://example.org:bad",
        "//example.org",
        "https://example.org\\bad",
    ],
)
def test_display_links_reject_dangerous_schemes_and_ambiguity(url):
    assert not safe_web_url(url)


def test_display_links_allow_normal_event_urls():
    assert safe_web_url("https://example.org/events?id=2")


def test_access_log_removes_private_query():
    record = logging.LogRecord(
        "uvicorn.access",
        20,
        "",
        0,
        "%s %s %s %s %s",
        ("127.0.0.1", "GET", "/api/markets?lat=48&lon=11", "1.1", 200),
        None,
    )
    assert PrivateAccessLog().filter(record)
    assert "lat=" not in record.getMessage()
    assert "/api/markets" in record.getMessage()


def test_instance_lock_excludes_sibling_and_releases(tmp_path):
    db = tmp_path / "private" / "app.db"
    owner = InstanceLock(db)
    try:
        with pytest.raises(RuntimeError, match="Another"):
            InstanceLock(db)
        assert db.parent.stat().st_mode & 0o777 == 0o700
    finally:
        owner.close()
    InstanceLock(db).close()
    InstanceLock(Path(":memory:")).close()


@pytest.mark.parametrize(
    "target",
    [
        "https://127.0.0.1/private",
        "http://source.example/events",
        "https://169.254.169.254/",
        "https://[::1]/",
        "https://evil.example/",
        "https://source.example:444/",
        "https://u:p@source.example/",
    ],
)
async def test_forbidden_redirect_is_never_requested(target):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"Location": target})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as raw:
        client = PoliteHttpClient(raw, 0, 0).for_source("https://source.example")
        with pytest.raises(httpx.RequestError):
            await client.get("https://source.example/start")
        assert seen == ["https://source.example/start"]


async def test_response_and_redirect_budgets(monkeypatch):
    monkeypatch.setattr(
        "ritterradar.crawler.http_client.get_settings",
        lambda: Settings(_env_file=None, max_response_bytes=1024),
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"x" * 1025))
    ) as raw:
        with pytest.raises(httpx.RequestError, match="byte budget"):
            await PoliteHttpClient(raw, 0, 0).get("https://example.org/")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(302, headers={"Location": "/loop"}))
    ) as raw:
        with pytest.raises(httpx.RequestError, match="Too many redirects"):
            await PoliteHttpClient(raw, 0, 0).get("https://example.org/")


async def test_redirect_hops_consume_request_budget(monkeypatch):
    monkeypatch.setattr(
        "ritterradar.crawler.http_client.get_settings",
        lambda: Settings(_env_file=None, max_crawl_pages=1),
    )
    seen = []

    def redirect(request):
        seen.append(request.url)
        return httpx.Response(302, headers={"Location": "/loop"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(redirect)) as raw:
        client = PoliteHttpClient(raw, 0, 0)
        with pytest.raises(httpx.RequestError, match="Too many redirects"):
            await client.get("https://example.org/")
        with pytest.raises(httpx.RequestError, match="request budget"):
            await client.get("https://example.org/")
    assert len(seen) == 11


async def test_dns_validation_pins_the_connected_address(monkeypatch):
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(
        loop,
        "getaddrinfo",
        AsyncMock(
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        ),
    )
    connect = AsyncMock(return_value="stream")
    monkeypatch.setattr("ritterradar.crawler.network.AutoBackend.connect_tcp", connect)
    backend = PublicNetworkBackend()
    assert await backend.connect_tcp("source.example", 443) == "stream"
    assert connect.call_args.args[0] == "93.184.216.34"
    monkeypatch.setattr(
        loop,
        "getaddrinfo",
        AsyncMock(return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]),
    )
    connect.reset_mock()
    with pytest.raises(httpcore.ConnectError):
        await backend.connect_tcp("source.example", 443)
    connect.assert_not_called()


def test_geocoder_uses_bounded_allowlisted_transport(monkeypatch):
    seen = []

    def handler(request):
        seen.append((str(request.url), request.headers["user-agent"]))
        return httpx.Response(200, json=[{"lat": "52.5", "lon": "13.4"}])

    monkeypatch.setattr(
        "ritterradar.geocoding.transport.make_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(
        "ritterradar.crawler.http_client.get_settings", lambda: Settings(_env_file=None)
    )
    adapter = SafeGeocoderAdapter(proxies=None, ssl_context=None)
    assert (
        adapter.get_json(
            "https://nominatim.openstreetmap.org/search?q=Berlin",
            timeout=2,
            headers={"User-Agent": "RitterRadar/test"},
        )[0]["lat"]
        == "52.5"
    )
    with pytest.raises(httpx.RequestError):
        adapter.get_json(
            "https://evil.example/search?q=Berlin",
            timeout=2,
            headers={"User-Agent": "RitterRadar/test"},
        )
    assert seen == [("https://nominatim.openstreetmap.org/search?q=Berlin", "RitterRadar/test")]


def test_invalid_ingested_coordinates_and_urls():
    values = {
        "name": "Medieval fair",
        "start_date": date(2026, 9, 1),
        "end_date": date(2026, 9, 2),
        "source_url": "https://example.org",
    }
    for extra in (
        {"latitude": "invalid", "longitude": 11},
        {"latitude": 999, "longitude": 11},
        {"source_url": "javascript:alert(1)"},
        {"market_type": '<img src=x onerror="x()">'},
    ):
        with pytest.raises(ValueError):
            validate_market(MarketData(**(values | extra)))
    assert validate_market(MarketData(**values, latitude=0, longitude=0)).latitude == 0


def test_duplicate_jobs_and_cooldown(secure_app, monkeypatch):
    from ritterradar.database.engine import get_engine

    with Session(get_engine()) as session:
        session.add(
            Source(
                name="Only source",
                base_url="https://source.example",
                adapter_name="spectaculum",
                enabled=True,
            )
        )
        session.commit()
    settings = secure_app[1]
    settings.workers = 1
    settings.offline = False
    queue = CrawlQueue(settings)
    # A new runner can have less than 60 seconds of monotonic uptime.
    with monkeypatch.context() as patch:
        patch.setattr("ritterradar.crawler.queue.time.monotonic", lambda: 1.0)
        assert queue.enqueue_all() == 1
        assert queue.enqueue_all() == 0
    assert queue._enqueue_all() == 0
    with Session(get_engine()) as session:
        assert len(session.exec(select(CrawlJob)).all()) == 1


async def test_zero_workers_cannot_leave_new_pending_jobs(secure_app):
    from ritterradar.database.engine import get_engine

    with Session(get_engine()) as session:
        session.add(
            Source(name="No worker", base_url="https://source.example", adapter_name="spectaculum")
        )
        session.commit()
    queue = CrawlQueue(secure_app[1])
    await queue.start()
    try:
        assert queue.enqueue_all() == 0
        assert queue._enqueue_all() == 0
        assert queue.get_status()["queue_size"] == 0
        with Session(get_engine()) as session:
            assert session.exec(select(CrawlJob)).all() == []
    finally:
        await queue.stop()


def test_loopback_hostnames_are_not_trusted():
    from ritterradar.security import is_loopback

    assert not is_loopback("localhost")
    assert not is_loopback("not-an-address")


async def test_security_middleware_bypasses_non_http_scopes(monkeypatch):
    seen = []

    async def downstream(scope, receive, send):
        seen.append(scope["type"])

    app = SecurityMiddleware(downstream)
    await app({"type": "websocket"}, AsyncMock(), AsyncMock())
    assert seen == ["websocket"]


async def test_security_rejects_concurrency_and_invalid_port(secure_app):
    app, settings = secure_app
    settings.request_concurrency = 0
    c = browser(app)
    assert c.get("/probe").status_code == 503
    settings.request_concurrency = 16
    assert c.get("/probe", headers={"Host": "localhost:99999"}).status_code == 400


async def _send_security_request(middleware, *, authorization: str = ""):
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/probe",
        "raw_path": b"/probe",
        "query_string": b"",
        "headers": [
            (b"host", b"localhost"),
            (b"authorization", authorization.encode()),
        ],
        "client": ("192.0.2.8", 1),
        "server": ("localhost", 80),
    }
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await middleware(scope, receive, send)
    return next(item["status"] for item in messages if item["type"] == "http.response.start")


async def test_expired_request_and_auth_windows_are_pruned(secure_app, monkeypatch):
    from collections import deque

    import ritterradar.security as security

    app, settings = secure_app
    settings.auth_token = SecretStr("a" * 32)

    async def noop(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = SecurityMiddleware(noop)
    middleware.requests = deque([0.0])
    middleware.auth_failures["192.0.2.8"] = deque([0.0])
    monkeypatch.setattr(security.time, "monotonic", lambda: 1000.0)
    assert await _send_security_request(middleware, authorization="Bearer wrong") == 401
    assert middleware.requests == deque([1000.0])
    assert middleware.auth_failures["192.0.2.8"] == deque([1000.0])
    # A valid credential clears the accumulated failures for its peer.
    assert await _send_security_request(middleware, authorization=f"Bearer {'a' * 32}") == 200
    assert "192.0.2.8" not in middleware.auth_failures


async def test_security_request_body_timeout_and_disconnect(secure_app, monkeypatch):
    import ritterradar.security as security

    app, _ = secure_app
    middleware = SecurityMiddleware(app)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/probe",
        "raw_path": b"/probe",
        "query_string": b"",
        "headers": [(b"host", b"localhost"), (b"x-ritterradar-request", b"1")],
        "client": ("127.0.0.1", 1),
        "server": ("localhost", 80),
    }
    messages = []

    async def send(message):
        messages.append(message)

    async def timeout(awaitable, timeout_seconds):
        awaitable.close()
        raise TimeoutError

    with monkeypatch.context() as patcher:
        patcher.setattr(security.asyncio, "wait_for", timeout)
        await middleware(scope, AsyncMock(), send)
    assert messages[0]["status"] == 408

    messages.clear()

    async def disconnect(awaitable, timeout_seconds):
        return await awaitable

    async def receive_disconnect():
        return {"type": "http.disconnect"}

    with monkeypatch.context() as patcher:
        patcher.setattr(security.asyncio, "wait_for", disconnect)
        await middleware(scope, receive_disconnect, send)
    assert messages == []


async def test_security_auth_failure_map_is_bounded(secure_app):
    from collections import deque

    _, settings = secure_app
    settings.auth_token = SecretStr("b" * 32)

    async def noop(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = SecurityMiddleware(noop)
    middleware.auth_failures = {str(i): deque() for i in range(1024)}
    assert await _send_security_request(middleware, authorization="Bearer wrong") == 401
    assert len(middleware.auth_failures) == 1024
    assert "0" not in middleware.auth_failures


async def test_security_replays_bounded_body_to_downstream():
    received = []

    async def downstream(scope, receive, send):
        received.append(await receive())
        received.append(await receive())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = SecurityMiddleware(downstream)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/probe",
        "raw_path": b"/probe",
        "query_string": b"",
        "headers": [(b"host", b"localhost"), (b"x-ritterradar-request", b"1")],
        "client": ("127.0.0.1", 1),
        "server": ("localhost", 80),
    }
    messages = iter(
        [
            {"type": "http.request", "body": b"abc", "more_body": True},
            {"type": "http.request", "body": b"def", "more_body": False},
            {"type": "http.request", "body": b"ignored", "more_body": False},
        ]
    )

    async def receive():
        return next(messages)

    await middleware(scope, receive, AsyncMock())
    assert received == [
        {"type": "http.request", "body": b"abcdef", "more_body": False},
        {"type": "http.request", "body": b"ignored", "more_body": False},
    ]
