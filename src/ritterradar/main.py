# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""RitterRadar FastAPI application — entry point and lifespan."""

import logging
import logging.config
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ritterradar.api.crawl import router as crawl_router
from ritterradar.api.markets import router as markets_router
from ritterradar.api.settings import router as settings_router
from ritterradar.api.sources import router as sources_router
from ritterradar.config import get_settings
from ritterradar.crawler.queue import CrawlQueue
from ritterradar.database.engine import create_tables

_BASE = Path(__file__).parent
_STATIC = _BASE / "static"
_TEMPLATES = _BASE / "templates"


def _configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    _configure_logging()
    logger = logging.getLogger(__name__)
    settings = get_settings()

    logger.info("RitterRadar starting up…")
    create_tables()
    logger.info("Database tables ready")

    queue = CrawlQueue(settings)
    app.state.crawl_queue = queue
    await queue.start()
    logger.info("Crawler queue started")

    yield  # ← application runs here

    logger.info("RitterRadar shutting down…")
    await queue.stop()
    logger.info("Crawler queue stopped")


app = FastAPI(
    title="RitterRadar",
    description="Discover German medieval markets on an interactive map",
    version="0.0.12",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Static files (CSS, JS, images)
if _STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

templates = Jinja2Templates(directory=str(_TEMPLATES))


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    """Serve the main single-page application."""
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


# Register routers
app.include_router(markets_router)
app.include_router(sources_router)
app.include_router(crawl_router)
app.include_router(settings_router)


def run() -> None:
    """Entry point for the `ritterradar` console script."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "ritterradar.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
