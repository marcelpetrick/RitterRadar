# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Geocoding cache model — avoids repeated Nominatim API calls."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class GeocodingCache(SQLModel, table=True):
    """Cached result of a geocoding query."""

    __tablename__ = "geocoding_cache"

    id: int | None = Field(default=None, primary_key=True)
    query: str = Field(unique=True, index=True)
    latitude: float
    longitude: float
    display_name: str = Field(default="")
    uncertain: bool = Field(default=False)
    cached_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
