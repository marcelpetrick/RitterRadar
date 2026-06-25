# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Abstract base class for all crawler adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ritterradar.crawler.http_client import PoliteHttpClient


@dataclass
class MarketData:
    """Raw market data extracted by an adapter, before geocoding and DB storage."""

    name: str
    start_date: date
    end_date: date
    market_type: str = "medieval"
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str = "DE"
    program_text: str | None = None
    original_text: str = ""
    source_url: str = ""
    confidence_score: float = 1.0
    tags: list[str] = field(default_factory=list)


class AbstractCrawlerAdapter(ABC):
    """Base class all site-specific crawlers must implement."""

    #: Human-readable name matching the Source.name in the database.
    SOURCE_NAME: str = ""
    #: Landing URL that will be crawled.
    BASE_URL: str = ""

    @abstractmethod
    async def crawl(self, client: "PoliteHttpClient") -> list[MarketData]:
        """Fetch pages and return extracted market records.

        Must not raise — callers rely on a list return (possibly empty).
        Internal exceptions should be caught and logged by the adapter.
        """
        ...
