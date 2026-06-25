# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Market database model."""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Market(SQLModel, table=True):
    """A medieval market or similar historical event."""

    __tablename__ = "market"
    __table_args__ = (
        UniqueConstraint("name", "start_date", "source_url", name="uq_market_identity"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Official event name")
    market_type: str = Field(
        default="medieval",
        description="medieval | renaissance | viking | fantasy | christmas",
    )
    start_date: date = Field(index=True)
    end_date: date
    address: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None, index=True)
    postal_code: Optional[str] = Field(default=None)
    country: str = Field(default="DE")
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    geocode_uncertain: bool = Field(default=False)
    program_text: Optional[str] = Field(default=None)
    original_text: str = Field(default="")
    source_url: str = Field(index=True)
    source_name: str
    hidden: bool = Field(default=False, index=True)
    confidence_score: float = Field(default=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
