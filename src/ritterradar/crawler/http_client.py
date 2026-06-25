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

import httpx

logger = logging.getLogger(__name__)

_MIN_DELAY = 0.5
_MAX_DELAY = 2.0
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0
_BACKOFF_MAX = 60.0
_TIMEOUT = 30.0

_USER_AGENT = (
    "RitterRadar/0.0 (German medieval market finder; "
    "https://github.com/mpetrick/RitterRadar)"
)


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


def make_client() -> httpx.AsyncClient:
    """Create an httpx.AsyncClient with sensible defaults."""
    return httpx.AsyncClient(
        headers={"User-Agent": _USER_AGENT},
        timeout=_TIMEOUT,
        follow_redirects=True,
    )
