# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Market database model."""

from datetime import UTC, date, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Market(SQLModel, table=True):
    """A medieval market or similar historical event."""

    __tablename__ = "market"
    __table_args__ = (
        UniqueConstraint("name", "start_date", "source_url", name="uq_market_identity"),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Official event name")
    market_type: str = Field(
        default="medieval",
        description="medieval | renaissance | viking | fantasy | christmas",
    )
    start_date: date = Field(index=True)
    end_date: date
    address: str | None = Field(default=None)
    city: str | None = Field(default=None, index=True)
    postal_code: str | None = Field(default=None)
    country: str = Field(default="DE")
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    geocode_uncertain: bool = Field(default=False)
    program_text: str | None = Field(default=None)
    original_text: str = Field(default="")
    source_url: str = Field(index=True)
    source_name: str
    hidden: bool = Field(default=False, index=True)
    confidence_score: float = Field(default=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
