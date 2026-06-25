# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""CrawlJob model — one execution of a crawler adapter against a Source."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class CrawlJob(SQLModel, table=True):
    """Tracks the lifecycle of a single crawl attempt for one source."""

    __tablename__ = "crawl_job"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="source.id", index=True)
    source_name: str
    status: str = Field(
        default="pending",
        description="pending | running | completed | failed | skipped",
        index=True,
    )
    started_at: Optional[datetime] = Field(default=None)
    finished_at: Optional[datetime] = Field(default=None)
    events_discovered: int = Field(default=0)
    events_inserted: int = Field(default=0)
    events_updated: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)
