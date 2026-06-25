# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""SQLModel table models — import all to register them with SQLAlchemy metadata."""

from ritterradar.models.crawl_job import CrawlJob
from ritterradar.models.geocoding_cache import GeocodingCache
from ritterradar.models.market import Market
from ritterradar.models.source import Source
from ritterradar.models.user_settings import UserSettings

__all__ = ["Market", "Source", "CrawlJob", "UserSettings", "GeocodingCache"]
