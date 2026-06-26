# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""CrawlQueue — manages job lifecycle and spawns CrawlWorker tasks."""

import asyncio
import logging
from pathlib import Path

import yaml
from sqlmodel import Session, select

from ritterradar.config import Settings
from ritterradar.crawler.worker import CrawlWorker
from ritterradar.database.engine import get_engine
from ritterradar.models.crawl_job import CrawlJob
from ritterradar.models.source import Source

logger = logging.getLogger(__name__)


class CrawlQueue:
    """Orchestrates background crawling.

    On ``start()``:
    1. Seeds the Source table from sources.yaml (upsert by name).
    2. Enqueues a CrawlJob for every enabled source.
    3. Spawns ``N`` CrawlWorker tasks that drain the queue.

    On ``stop()``:  Sends sentinel ``None`` values to wake workers, then
    waits for all tasks to finish.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._queue: asyncio.Queue[int | None] = asyncio.Queue()
        self._workers: list[CrawlWorker] = []

    async def start(self) -> None:
        self._seed_sources()
        self._enqueue_all()
        for i in range(self._settings.workers):
            w = CrawlWorker(self._queue, worker_id=i)
            w.start()
            self._workers.append(w)
        logger.info("CrawlQueue: started %d workers", self._settings.workers)

    async def stop(self) -> None:
        for _ in self._workers:
            await self._queue.put(None)
        for w in self._workers:
            await w.stop()
        logger.info("CrawlQueue: all workers stopped")

    def enqueue_all(self) -> int:
        """Public method: re-enqueue all enabled sources. Returns job count."""
        return self._enqueue_all()

    def _seed_sources(self) -> None:
        sources_file = Path(self._settings.sources_file)
        if not sources_file.exists():
            logger.warning("Sources file not found: %s", sources_file)
            return

        with open(sources_file, encoding="utf-8") as fh:
            config = yaml.safe_load(fh)

        if not isinstance(config, dict) or "sources" not in config:
            logger.warning("sources.yaml missing 'sources' key")
            return

        with Session(get_engine()) as session:
            for entry in config["sources"]:
                name = entry.get("name", "")
                existing = session.exec(select(Source).where(Source.name == name)).first()
                if existing is None:
                    session.add(
                        Source(
                            name=name,
                            base_url=entry.get("url", ""),
                            adapter_name=entry.get("adapter", ""),
                            enabled=entry.get("enabled", True),
                            crawl_interval_hours=entry.get(
                                "crawl_interval_hours",
                                self._settings.crawl_interval_hours,
                            ),
                        )
                    )
                else:
                    existing.base_url = entry.get("url", existing.base_url)
                    existing.adapter_name = entry.get("adapter", existing.adapter_name)
                    existing.enabled = entry.get("enabled", existing.enabled)
                    session.add(existing)
            session.commit()
        logger.info("CrawlQueue: sources seeded from %s", sources_file)

    def _enqueue_all(self) -> int:
        count = 0
        with Session(get_engine()) as session:
            sources = session.exec(select(Source).where(Source.enabled == True)).all()  # noqa: E712
            for source in sources:
                job = CrawlJob(
                    source_id=source.id or 0,
                    source_name=source.name,
                    status="pending",
                )
                session.add(job)
                session.flush()
                job_id = job.id
                session.commit()
                if job_id is not None:
                    self._queue.put_nowait(job_id)
                    count += 1
        logger.info("CrawlQueue: enqueued %d jobs", count)
        return count

    def get_status(self) -> dict[str, object]:
        """Return a summary of queue and recent job states."""
        with Session(get_engine()) as session:
            jobs = session.exec(
                select(CrawlJob).order_by(CrawlJob.id.desc()).limit(100)  # type: ignore[union-attr]
            ).all()

        counts: dict[str, int] = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
        }
        for job in jobs:
            if job.status in counts:
                counts[job.status] += 1

        return {
            "queue_size": self._queue.qsize(),
            "workers": len(self._workers),
            **counts,
            "recent_jobs": [
                {
                    "id": j.id,
                    "source_name": j.source_name,
                    "status": j.status,
                    "started_at": j.started_at.isoformat() if j.started_at else None,
                    "finished_at": j.finished_at.isoformat() if j.finished_at else None,
                    "events_discovered": j.events_discovered,
                    "events_inserted": j.events_inserted,
                    "error_message": j.error_message,
                }
                for j in jobs[:20]
            ],
        }
