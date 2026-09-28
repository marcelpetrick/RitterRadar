# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded HTTPS crawling with explicit host and redirect policies."""

import asyncio
import ipaddress
import logging
import random
from urllib.parse import urlsplit

import httpx

from ritterradar.config import get_settings
from ritterradar.crawler.network import PublicTransport

logger = logging.getLogger(__name__)
_MIN_DELAY = 0.5
_MAX_DELAY = 2.0
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0
_BACKOFF_MAX = 60.0
_TIMEOUT = 30.0
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"


def _domain_root(host: str) -> str:
    """Legacy display helper; never used for authorization."""
    parts = host.lower().rstrip(".").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


class PoliteHttpClient:
    """Request budget is scoped to one crawl via ``for_source``.

    HTTPS only, no URL credentials, explicit host allowlist, at most five
    redirects, decoded-byte cap, and a wall-clock deadline including retries.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        min_delay: float = _MIN_DELAY,
        max_delay: float = _MAX_DELAY,
        max_retries: int = _MAX_RETRIES,
        allowed_hosts: frozenset[str] | None = None,
        user_agent: str = _USER_AGENT,
    ) -> None:
        self._client = client
        self._min_delay, self._max_delay = min_delay, max_delay
        self._max_retries = max_retries
        self._allowed_hosts = allowed_hosts
        self._user_agent = user_agent
        self._requests = 0
        self.failures = 0

    def for_source(self, base_url: str) -> "PoliteHttpClient":
        host = urlsplit(base_url).hostname or ""
        root = host.removeprefix("www.")
        return PoliteHttpClient(
            self._client,
            self._min_delay,
            self._max_delay,
            self._max_retries,
            frozenset({root, "www." + root}),
        )

    def _validate(self, url: str) -> httpx.URL:
        try:
            target = httpx.URL(url)
            if (
                target.scheme != "https"
                or not target.host
                or target.port not in (None, 443)
                or target.userinfo
                or any(ord(c) <= 32 or c == "\\" for c in url)
            ):
                raise ValueError
            try:
                address = ipaddress.ip_address(target.host)
            except ValueError:
                address = None
            if address is not None and not address.is_global:
                raise ValueError
            if self._allowed_hosts is not None and target.host not in self._allowed_hosts:
                raise ValueError
        except (ValueError, httpx.InvalidURL):
            raise httpx.RequestError("Domain drift or disallowed crawler destination") from None
        return target

    async def get(self, url: str, **kwargs: object) -> httpx.Response:
        try:
            async with asyncio.timeout(60):
                return await self._get(url, **kwargs)
        except Exception:
            self.failures += 1
            raise

    async def _get(self, url: str, **kwargs: object) -> httpx.Response:
        settings = get_settings()
        if settings.offline:
            raise httpx.RequestError("Crawling disabled in offline mode")
        initial = self._validate(url)
        hosts = self._allowed_hosts or frozenset({initial.host, "www." + initial.host})
        await self._sleep()
        for attempt in range(self._max_retries + 1):
            try:
                target = initial
                response = None
                for _ in range(6):
                    self._validate(str(target))
                    if target.host not in hosts:
                        raise httpx.RequestError("Domain drift: redirect host is not allowed")
                    self._requests += 1
                    if self._requests > settings.max_crawl_pages + 10:
                        raise httpx.RequestError("Crawl request budget exceeded")
                    async with self._client.stream(
                        "GET",
                        target,
                        timeout=_TIMEOUT,
                        follow_redirects=False,
                        headers={"User-Agent": self._user_agent, "Accept-Encoding": "identity"},
                        **kwargs,  # type: ignore[arg-type]
                    ) as streamed:
                        if streamed.is_redirect:
                            location = streamed.headers.get("location")
                            if not location:
                                raise httpx.RequestError("Redirect missing Location")
                            target = target.join(location)
                            continue
                        # Identity encoding avoids decompression bombs before the
                        # decoded stream can enforce its own size limit.
                        if streamed.headers.get("content-encoding", "identity").lower() not in (
                            "identity",
                            "",
                        ):
                            raise httpx.RequestError("Compressed crawler responses are unsupported")
                        length = streamed.headers.get("content-length")
                        if length and int(length) > settings.max_response_bytes:
                            raise httpx.RequestError("Response exceeds byte budget")
                        body = bytearray()
                        async for chunk in streamed.aiter_bytes(chunk_size=65536):
                            body.extend(chunk)
                            if len(body) > settings.max_response_bytes:
                                raise httpx.RequestError("Response exceeds byte budget")
                        response = httpx.Response(
                            streamed.status_code,
                            headers=streamed.headers,
                            content=bytes(body),
                            request=streamed.request,
                        )
                        break
                if response is None:
                    raise httpx.RequestError("Too many redirects")
                if response.status_code not in (429, 503) or attempt == self._max_retries:
                    if response.is_error:
                        self.failures += 1
                    return response
            except httpx.TransportError:
                if attempt == self._max_retries:
                    raise httpx.RequestError("Network retries exhausted") from None
            await asyncio.sleep(min(_BACKOFF_BASE**attempt, _BACKOFF_MAX))
        raise httpx.RequestError("Network retries exhausted")

    async def _sleep(self) -> None:
        await asyncio.sleep(random.uniform(self._min_delay, self._max_delay))


def make_client() -> httpx.AsyncClient:
    """TLS verification and public-destination enforcement cannot be disabled."""
    return httpx.AsyncClient(
        transport=PublicTransport(),
        trust_env=False,
        timeout=_TIMEOUT,
        headers={"User-Agent": _USER_AGENT, "Accept-Language": "de-DE,de;q=0.9,en;q=0.5"},
        follow_redirects=False,
    )
