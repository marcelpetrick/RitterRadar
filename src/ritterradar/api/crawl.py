# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Crawl API — queue status and manual trigger."""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/crawl", tags=["crawl"])


@router.get("/status")
async def crawl_status(request: Request) -> dict[str, object]:
    """Return current crawl queue state and recent job summaries."""
    queue = getattr(request.app.state, "crawl_queue", None)
    if queue is None:
        return {"error": "crawler not initialised"}
    return queue.get_status()  # type: ignore[no-any-return]


@router.post("/trigger")
async def trigger_crawl(request: Request) -> dict[str, object]:
    """Enqueue all enabled sources for immediate crawling."""
    queue = getattr(request.app.state, "crawl_queue", None)
    if queue is None:
        return {"error": "crawler not initialised", "enqueued": 0}
    count: int = queue.enqueue_all()
    return {"enqueued": count, "message": f"Enqueued {count} crawl jobs"}
