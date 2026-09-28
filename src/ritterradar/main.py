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
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from importlib.metadata import version as _pkg_version
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, text

from ritterradar.api.crawl import router as crawl_router
from ritterradar.api.markets import router as markets_router
from ritterradar.api.settings import router as settings_router
from ritterradar.api.sources import router as sources_router
from ritterradar.config import get_settings
from ritterradar.crawler.queue import CrawlQueue
from ritterradar.database.engine import create_tables, get_engine
from ritterradar.runtime import InstanceLock, private_file
from ritterradar.security import PrivateAccessLog, SecurityMiddleware

_BASE = Path(__file__).parent
_STATIC = _BASE / "static"
_TEMPLATES = _BASE / "templates"


def _configure_logging() -> None:
    settings = get_settings()
    # force=True overrides any root-logger config uvicorn set before us
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)-40s %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    logging.getLogger("uvicorn.access").addFilter(PrivateAccessLog())
    if str(settings.db_path) != ":memory:":
        path = settings.db_path.parent / "ritterradar.log"
        handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        private_file(path)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logging.getLogger().addHandler(handler)
    # Suppress noisy third-party loggers at WARNING level
    for noisy in ("httpx", "httpcore", "geopy", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger = logging.getLogger(__name__)
    settings = get_settings()

    ownership = InstanceLock(settings.db_path)
    try:
        _configure_logging()
        logger.info("RitterRadar starting up… version=%s", _VERSION)
        create_tables()
        private_file(settings.db_path)
        queue = CrawlQueue(settings)
        app.state.crawl_queue = queue
        await queue.start()
        try:
            yield
        finally:
            await queue.stop()
    finally:
        ownership.close()


_VERSION = _pkg_version("ritterradar")

app = FastAPI(
    title="RitterRadar",
    description="Discover German medieval markets on an interactive map",
    version=_VERSION,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(SecurityMiddleware)

# Static files (CSS, JS, images)
if _STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

templates = Jinja2Templates(directory=str(_TEMPLATES))


@app.middleware("http")
async def add_static_cache_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
    return response


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    """Serve the main single-page application."""
    return templates.TemplateResponse(
        request, "index.html", {"version": _VERSION, "offline": get_settings().offline}
    )


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
async def readiness() -> JSONResponse:
    try:
        with Session(get_engine()) as session:
            session.exec(text("SELECT 1"))  # type: ignore[call-overload]
        queue = getattr(app.state, "crawl_queue", None)
        healthy = queue is not None and all(
            worker._task is not None and not worker._task.done() for worker in queue._workers
        )
    except Exception:
        healthy = False
    return JSONResponse({"ready": healthy}, status_code=200 if healthy else 503)


@app.get("/api/docs", response_class=HTMLResponse, include_in_schema=False)
@app.get("/api/redoc", response_class=HTMLResponse, include_in_schema=False)
async def api_reference(request: Request) -> HTMLResponse:
    """Local API reference: no third-party JavaScript or inline script."""
    return templates.TemplateResponse(request, "api.html", {"schema": app.openapi()})


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
        access_log=False,
    )
