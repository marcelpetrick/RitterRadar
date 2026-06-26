# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""UserSettings model — single-row table for the local user profile."""

from sqlmodel import Field, SQLModel


class UserSettings(SQLModel, table=True):
    """One-row table: id is always 1 (upserted, never multiple rows)."""

    __tablename__ = "user_settings"

    id: int = Field(default=1, primary_key=True)
    home_latitude: float | None = Field(default=None)
    home_longitude: float | None = Field(default=None)
    home_label: str | None = Field(default=None, description="Display label for the home pin")
    default_radius_km: float = Field(default=100.0)
    default_month_offset_start: int = Field(default=0, description="0 = current month")
    default_month_offset_end: int = Field(default=12)
