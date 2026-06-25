# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Crawler worker — processes one CrawlJob at a time with full failure isolation."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ritterradar.config import get_settings
from ritterradar.crawler.base_adapter import MarketData
from ritterradar.crawler.http_client import PoliteHttpClient, make_client
from ritterradar.crawler.registry import get_adapter
from ritterradar.database.engine import get_engine
from ritterradar.geocoding.nominatim import geocode
from ritterradar.models.crawl_job import CrawlJob
from ritterradar.models.market import Market
from ritterradar.models.source import Source

logger = logging.getLogger(__name__)


class CrawlWorker:
    """Pulls jobs from an asyncio.Queue and processes them one by one."""

    def __init__(self, queue: "asyncio.Queue[int | None]", worker_id: int) -> None:
        self._queue = queue
        self._worker_id = worker_id
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name=f"crawler-worker-{self._worker_id}")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        async with make_client() as http:
            client = PoliteHttpClient(http)
            while True:
                job_id = await self._queue.get()
                if job_id is None:
                    self._queue.task_done()
                    break
                try:
                    await self._process(job_id, client)
                except Exception:
                    logger.exception("Worker %d: unhandled error for job %d", self._worker_id, job_id)
                finally:
                    self._queue.task_done()

    async def _process(self, job_id: int, client: PoliteHttpClient) -> None:
        settings = get_settings()
        with Session(get_engine()) as session:
            job = session.get(CrawlJob, job_id)
            if job is None:
                logger.error("Worker %d: job %d not found in DB", self._worker_id, job_id)
                return

            source = session.get(Source, job.source_id)
            if source is None or not source.enabled:
                job.status = "skipped"
                session.add(job)
                session.commit()
                return

            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            session.add(job)
            session.commit()

        logger.info("Worker %d: crawling %s", self._worker_id, job.source_name)
        try:
            adapter = get_adapter(source.adapter_name)
        except KeyError:
            await self._fail(job_id, f"Unknown adapter: {source.adapter_name!r}")
            return

        try:
            markets = await adapter.crawl(client)
        except Exception as exc:
            await self._fail(job_id, str(exc))
            await self._update_source_error(source.id, str(exc))
            return

        inserted = updated = 0
        user_agent = f"RitterRadar/0.0 ({settings.geocoder_email})"

        for mdata in markets:
            lat, lon, uncertain = None, None, False
            geo_query = _build_geo_query(mdata)
            if geo_query:
                result = await geocode(geo_query, user_agent)
                if result:
                    lat, lon, uncertain = result.latitude, result.longitude, result.uncertain

            ins, upd = _upsert_market(mdata, lat, lon, uncertain, source.name)
            inserted += ins
            updated += upd

        await self._complete(job_id, len(markets), inserted, updated)
        await self._update_source_success(source.id)
        logger.info(
            "Worker %d: %s done — %d found, %d inserted, %d updated",
            self._worker_id,
            job.source_name,
            len(markets),
            inserted,
            updated,
        )

    async def _fail(self, job_id: int, error: str) -> None:
        with Session(get_engine()) as session:
            job = session.get(CrawlJob, job_id)
            if job:
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                job.error_message = error[:2000]
                session.add(job)
                session.commit()
        logger.error("Job %d failed: %s", job_id, error)

    async def _complete(
        self, job_id: int, discovered: int, inserted: int, updated: int
    ) -> None:
        with Session(get_engine()) as session:
            job = session.get(CrawlJob, job_id)
            if job:
                job.status = "completed"
                job.finished_at = datetime.now(timezone.utc)
                job.events_discovered = discovered
                job.events_inserted = inserted
                job.events_updated = updated
                session.add(job)
                session.commit()

    async def _update_source_error(self, source_id: int | None, error: str) -> None:
        if source_id is None:
            return
        with Session(get_engine()) as session:
            src = session.get(Source, source_id)
            if src:
                src.last_crawled_at = datetime.now(timezone.utc)
                src.last_error = error[:2000]
                session.add(src)
                session.commit()

    async def _update_source_success(self, source_id: int | None) -> None:
        if source_id is None:
            return
        with Session(get_engine()) as session:
            src = session.get(Source, source_id)
            if src:
                now = datetime.now(timezone.utc)
                src.last_crawled_at = now
                src.last_success_at = now
                src.last_error = None
                session.add(src)
                session.commit()


def _build_geo_query(mdata: MarketData) -> str:
    parts = []
    if mdata.postal_code:
        parts.append(mdata.postal_code)
    if mdata.city:
        parts.append(mdata.city)
    if not parts and mdata.address:
        parts.append(mdata.address)
    return ", ".join(parts) if parts else ""


def _upsert_market(
    mdata: MarketData,
    lat: float | None,
    lon: float | None,
    uncertain: bool,
    source_name: str,
) -> tuple[int, int]:
    with Session(get_engine()) as session:
        existing = session.exec(
            select(Market).where(
                Market.name == mdata.name,
                Market.start_date == mdata.start_date,
                Market.source_url == mdata.source_url,
            )
        ).first()

        now = datetime.now(timezone.utc)
        if existing is None:
            market = Market(
                name=mdata.name,
                market_type=mdata.market_type,
                start_date=mdata.start_date,
                end_date=mdata.end_date,
                address=mdata.address,
                city=mdata.city,
                postal_code=mdata.postal_code,
                country=mdata.country,
                latitude=lat,
                longitude=lon,
                geocode_uncertain=uncertain,
                program_text=mdata.program_text,
                original_text=mdata.original_text,
                source_url=mdata.source_url,
                source_name=source_name,
                confidence_score=mdata.confidence_score,
                created_at=now,
                updated_at=now,
            )
            try:
                session.add(market)
                session.commit()
                return 1, 0
            except IntegrityError:
                session.rollback()
                return 0, 0
        else:
            existing.end_date = mdata.end_date
            existing.address = mdata.address
            existing.city = mdata.city
            existing.postal_code = mdata.postal_code
            if lat is not None:
                existing.latitude = lat
                existing.longitude = lon
                existing.geocode_uncertain = uncertain
            existing.program_text = mdata.program_text
            existing.original_text = mdata.original_text
            existing.updated_at = now
            session.add(existing)
            session.commit()
            return 0, 1
