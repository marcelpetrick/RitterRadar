# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Abstract base class for all crawler adapters."""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Annotated

from pydantic import Field, TypeAdapter

from ritterradar.security import safe_web_url

if TYPE_CHECKING:
    from ritterradar.crawler.http_client import PoliteHttpClient


@dataclass
class MarketData:
    """Raw market data extracted by an adapter, before geocoding and DB storage."""

    name: Annotated[str, Field(min_length=1, max_length=500)]
    start_date: date
    end_date: date
    market_type: Annotated[
        str, Field(pattern=r"^(medieval|renaissance|viking|fantasy|christmas)$")
    ] = "medieval"
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str = "DE"
    program_text: str | None = None
    original_text: str = ""
    source_url: str = ""
    confidence_score: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] = 1.0
    tags: list[str] = field(default_factory=list)
    # Adapters that already have coordinates (e.g. via a JSON API) may set these
    # to skip Nominatim geocoding entirely.
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)] | None = None
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)] | None = None


def validate_market(value: MarketData) -> MarketData:
    """Validate every adapter before coordinates or text enter persistence."""
    validated = TypeAdapter(MarketData).validate_python(asdict(value))
    if not safe_web_url(validated.source_url):
        raise ValueError("Invalid event source URL")
    if (validated.latitude is None) != (validated.longitude is None):
        raise ValueError("Incomplete event coordinates")
    for name in ("address", "city", "postal_code", "country", "program_text", "original_text"):
        text = getattr(validated, name)
        if text is not None and (not isinstance(text, str) or len(text) > 10000):
            raise ValueError("Invalid or oversized event field")
    return validated


class AbstractCrawlerAdapter(ABC):
    """Base class all site-specific crawlers must implement."""

    #: Human-readable name matching the Source.name in the database.
    SOURCE_NAME: str = ""
    #: Landing URL that will be crawled.
    BASE_URL: str = ""

    @abstractmethod
    async def crawl(self, client: "PoliteHttpClient") -> list[MarketData]:
        """Fetch pages and return extracted market records.

        Raise on fetch/parse failure. An empty list means a successful empty feed.
        """
        ...
