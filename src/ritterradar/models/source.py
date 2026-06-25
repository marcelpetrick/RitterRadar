# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Source database model — a configured crawl target."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Source(SQLModel, table=True):
    """A website from which markets are crawled."""

    __tablename__ = "source"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    base_url: str
    adapter_name: str
    enabled: bool = Field(default=True)
    crawl_interval_hours: int = Field(default=24)
    last_crawled_at: Optional[datetime] = Field(default=None)
    last_success_at: Optional[datetime] = Field(default=None)
    last_error: Optional[str] = Field(default=None)
