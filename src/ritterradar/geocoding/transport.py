# SPDX-License-Identifier: GPL-3.0-or-later
"""Geopy adapter using the same bounded, public-IP-only transport as crawling."""

import asyncio
import json
from typing import Any

from geopy.adapters import BaseSyncAdapter

from ritterradar.crawler.http_client import PoliteHttpClient, make_client


class SafeGeocoderAdapter(BaseSyncAdapter):  # type: ignore[misc]
    def get_text(self, url: str, *, timeout: float, headers: dict[str, str]) -> str:
        async def fetch() -> str:
            async with asyncio.timeout(timeout):
                async with make_client() as raw:
                    client = PoliteHttpClient(
                        raw,
                        0,
                        0,
                        0,
                        frozenset({"nominatim.openstreetmap.org"}),
                        user_agent=headers.get("User-Agent", "RitterRadar"),
                    )
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.text

        return asyncio.run(fetch())

    def get_json(self, url: str, *, timeout: float, headers: dict[str, str]) -> Any:
        return json.loads(self.get_text(url, timeout=timeout, headers=headers))
