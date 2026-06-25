# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Polite async HTTP client with random delays, retries, and backoff."""

import asyncio
import logging
import random
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_MIN_DELAY = 0.5
_MAX_DELAY = 2.0
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0
_BACKOFF_MAX = 60.0
_TIMEOUT = 30.0

# Realistic browser UA — many sites block non-browser strings outright
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
)


def _domain_root(host: str) -> str:
    """Return the eTLD+1 of a hostname (e.g. 'sedo.com' from 'www.sedo.com')."""
    parts = host.lower().rstrip(".").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


class PoliteHttpClient:
    """Wraps an httpx.AsyncClient with polite crawling behaviour.

    - Random delay between requests (0.5–2.0 s by default).
    - Exponential backoff on transient errors (429, 503, network errors).
    - Consistent User-Agent header.
    - Hard timeout of 30 s per request.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        min_delay: float = _MIN_DELAY,
        max_delay: float = _MAX_DELAY,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self._client = client
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._max_retries = max_retries

    async def get(self, url: str, **kwargs: object) -> httpx.Response:
        """Perform a GET request with delay and retry logic."""
        await self._sleep()
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(
                    url,
                    timeout=_TIMEOUT,
                    headers={"User-Agent": _USER_AGENT},
                    follow_redirects=True,
                    **kwargs,  # type: ignore[arg-type]
                )
                # Detect domain parking: if we end up on a completely different
                # domain the original site is probably expired / redirected away.
                req_root = _domain_root(urlparse(url).hostname or "")
                resp_root = _domain_root(str(response.url.host))
                if req_root and resp_root and req_root != resp_root:
                    raise httpx.RequestError(
                        f"Domain drift: requested {url!r} but landed on"
                        f" {str(response.url)!r} — parked or hijacked domain"
                    )

                if response.status_code in (429, 503) and attempt < self._max_retries:
                    backoff = min(_BACKOFF_BASE**attempt, _BACKOFF_MAX)
                    logger.warning(
                        "HTTP %d for %s; retrying in %.1fs (attempt %d/%d)",
                        response.status_code,
                        url,
                        backoff,
                        attempt + 1,
                        self._max_retries,
                    )
                    await asyncio.sleep(backoff)
                    continue
                return response
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    backoff = min(_BACKOFF_BASE**attempt, _BACKOFF_MAX)
                    logger.warning(
                        "Network error for %s: %s; retrying in %.1fs (attempt %d/%d)",
                        url,
                        exc,
                        backoff,
                        attempt + 1,
                        self._max_retries,
                    )
                    await asyncio.sleep(backoff)

        raise httpx.RequestError(f"All {self._max_retries} retries exhausted for {url}") from (
            last_exc
        )

    async def _sleep(self) -> None:
        delay = random.uniform(self._min_delay, self._max_delay)
        await asyncio.sleep(delay)


def make_client(verify: bool = True) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient with sensible defaults."""
    return httpx.AsyncClient(
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
        },
        timeout=_TIMEOUT,
        follow_redirects=True,
        verify=verify,
    )
