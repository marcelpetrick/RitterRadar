# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for crawl queue lifecycle recovery."""

from sqlmodel import Session, select

from ritterradar.config import Settings
from ritterradar.crawler.queue import CrawlQueue
from ritterradar.models.crawl_job import CrawlJob


def test_recover_interrupted_jobs_marks_only_active_states_skipped(session: Session):
    active_before = session.exec(
        select(CrawlJob).where(CrawlJob.status.in_(("pending", "running")))  # type: ignore[union-attr]
    ).all()
    jobs = [
        CrawlJob(source_id=901, source_name="Pending recovery", status="pending"),
        CrawlJob(source_id=902, source_name="Running recovery", status="running"),
        CrawlJob(source_id=903, source_name="Completed recovery", status="completed"),
    ]
    session.add_all(jobs)
    session.commit()

    queue = CrawlQueue(Settings(workers=0))
    assert queue._recover_interrupted_jobs() == len(active_before) + 2

    recovered = session.exec(
        select(CrawlJob).where(CrawlJob.source_id.in_((901, 902, 903)))  # type: ignore[union-attr]
    ).all()
    session.expire_all()
    by_source = {job.source_id: job for job in recovered}
    assert by_source[901].status == "skipped"
    assert by_source[902].status == "skipped"
    assert by_source[901].finished_at is not None
    assert by_source[901].error_message == "Interrupted by application shutdown"
    assert by_source[903].status == "completed"
