# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for the crawl worker job lifecycle (adapters and geocoder stubbed)."""

import asyncio
from datetime import date

from sqlmodel import Session, select

import ritterradar.crawler.worker as worker_mod
from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.worker import CrawlWorker, _build_geo_query, _upsert_market
from ritterradar.geocoding.nominatim import GeoResult
from ritterradar.models.crawl_job import CrawlJob
from ritterradar.models.market import Market
from ritterradar.models.source import Source


class _StubAdapter(AbstractCrawlerAdapter):
    def __init__(self, markets: list[MarketData] | None = None, error: Exception | None = None):
        self.markets = markets or []
        self.error = error

    async def crawl(self, client):  # type: ignore[no-untyped-def]
        if self.error:
            raise self.error
        return self.markets


def _make_job(session: Session, name: str, enabled: bool = True) -> tuple[int, int]:
    source = Source(name=name, base_url="https://example.com", adapter_name="stub", enabled=enabled)
    session.add(source)
    session.commit()
    session.refresh(source)
    assert source.id is not None
    job = CrawlJob(source_id=source.id, source_name=name)
    session.add(job)
    session.commit()
    session.refresh(job)
    assert job.id is not None
    return source.id, job.id


def _new_job(session: Session, source_id: int, name: str) -> int:
    job = CrawlJob(source_id=source_id, source_name=name)
    session.add(job)
    session.commit()
    session.refresh(job)
    assert job.id is not None
    return job.id


def _worker() -> CrawlWorker:
    return CrawlWorker(asyncio.Queue(), worker_id=1)


async def test_missing_job_is_ignored():
    await _worker()._process(987654, None)  # type: ignore[arg-type]


async def test_disabled_source_marks_job_skipped(session: Session):
    _, job_id = _make_job(session, "Worker disabled source", enabled=False)
    await _worker()._process(job_id, None)  # type: ignore[arg-type]
    session.expire_all()
    job = session.get(CrawlJob, job_id)
    assert job is not None
    assert job.status == "skipped"


async def test_unknown_adapter_fails_job(session: Session, monkeypatch):
    def unknown(name: str):
        raise KeyError(name)

    monkeypatch.setattr(worker_mod, "get_adapter", unknown)
    _, job_id = _make_job(session, "Worker unknown adapter")
    await _worker()._process(job_id, None)  # type: ignore[arg-type]
    session.expire_all()
    job = session.get(CrawlJob, job_id)
    assert job is not None
    assert job.status == "failed"
    assert job.error_message == "Unknown adapter: 'stub'"


async def test_adapter_error_fails_job_and_records_source_error(session: Session, monkeypatch):
    monkeypatch.setattr(
        worker_mod, "get_adapter", lambda name: _StubAdapter(error=RuntimeError("site down"))
    )
    source_id, job_id = _make_job(session, "Worker adapter error")
    await _worker()._process(job_id, None)  # type: ignore[arg-type]
    session.expire_all()
    job = session.get(CrawlJob, job_id)
    source = session.get(Source, source_id)
    assert job is not None and source is not None
    assert (job.status, job.error_message) == ("failed", "site down")
    assert job.finished_at is not None
    assert source.last_error == "site down"
    assert source.last_crawled_at is not None


async def test_successful_crawl_geocodes_only_what_is_needed(session: Session, monkeypatch):
    markets = [
        MarketData(
            name="Worker pre-geocoded market",
            start_date=date(2031, 5, 1),
            end_date=date(2031, 5, 2),
            postal_code="10115",
            city="Berlin",
            source_url="https://example.com/worker-1",
            latitude=52.53,
            longitude=13.38,
        ),
        MarketData(
            name="Worker geocoded market",
            start_date=date(2031, 5, 8),
            end_date=date(2031, 5, 9),
            postal_code="80331",
            city="München",
            source_url="https://example.com/worker-2",
        ),
        MarketData(
            name="Worker unlocated market",
            start_date=date(2031, 5, 15),
            end_date=date(2031, 5, 15),
            source_url="https://example.com/worker-3",
        ),
    ]
    calls: list[tuple[str, dict[str, object]]] = []

    async def fake_geocode(query: str, user_agent: str, **kwargs: object) -> GeoResult:
        calls.append((query, kwargs))
        return GeoResult(48.137, 11.575, "München", False)

    monkeypatch.setattr(worker_mod, "geocode", fake_geocode)
    monkeypatch.setattr(worker_mod, "get_adapter", lambda name: _StubAdapter(markets))
    source_id, job_id = _make_job(session, "Worker success source")

    await _worker()._process(job_id, None)  # type: ignore[arg-type]

    session.expire_all()
    job = session.get(CrawlJob, job_id)
    source = session.get(Source, source_id)
    assert job is not None and source is not None
    assert (job.status, job.events_discovered, job.events_inserted, job.events_updated) == (
        "completed",
        3,
        3,
        0,
    )
    assert source.last_success_at is not None and source.last_error is None
    assert calls == [
        ("80331, München", {"country_code": "DE", "postal_code": "80331", "city": "München"})
    ]
    geocoded = session.exec(select(Market).where(Market.name == "Worker geocoded market")).one()
    assert (geocoded.latitude, geocoded.longitude) == (48.137, 11.575)

    # A second crawl reuses trusted coordinates instead of geocoding again.
    second_job = _new_job(session, source_id, "Worker success source")
    await _worker()._process(second_job, None)  # type: ignore[arg-type]
    session.expire_all()
    job = session.get(CrawlJob, second_job)
    assert job is not None
    assert (job.events_inserted, job.events_updated) == (0, 3)
    assert len(calls) == 1


async def test_run_loop_survives_job_errors_and_stops_on_sentinel(monkeypatch):
    processed: list[int] = []

    async def fake_process(self: CrawlWorker, job_id: int, client: object) -> None:
        processed.append(job_id)
        if job_id == 2:
            raise RuntimeError("boom")

    monkeypatch.setattr(CrawlWorker, "_process", fake_process)
    queue: asyncio.Queue[int | None] = asyncio.Queue()
    for item in (1, 2, 3, None):
        queue.put_nowait(item)

    worker = CrawlWorker(queue, worker_id=0)
    worker.start()
    await asyncio.wait_for(queue.join(), timeout=5)
    await worker.stop()
    assert processed == [1, 2, 3]


async def test_stop_without_start_and_source_updates_without_id():
    worker = _worker()
    await worker.stop()
    await worker._update_source_error(None, "ignored")
    await worker._update_source_success(None)


def test_build_geo_query_prefers_postal_code_and_city_over_address():
    base = {"name": "Q", "start_date": date(2031, 1, 1), "end_date": date(2031, 1, 1)}
    assert _build_geo_query(MarketData(**base, postal_code="24103", city="Kiel")) == "24103, Kiel"
    assert _build_geo_query(MarketData(**base, address="Burg Rabenstein")) == "Burg Rabenstein"
    assert _build_geo_query(MarketData(**base)) == ""


def test_upsert_enriches_existing_market_from_another_source(session: Session):
    first = MarketData(
        name="Worker enrichment market",
        start_date=date(2031, 7, 1),
        end_date=date(2031, 7, 2),
        city="Kiel",
        source_url="https://example.com/enrich-a",
        original_text="short",
    )
    assert _upsert_market(first, None, None, False, "Source A") == (1, 0)

    richer = MarketData(
        name="Worker enrichment market",
        start_date=date(2031, 7, 1),
        end_date=date(2031, 7, 3),
        city="Kiel",
        postal_code="24103",
        address="Rathausplatz",
        program_text="Musik und Gaukler",
        original_text="a much longer original text",
        source_url="https://example.com/enrich-b",
    )
    assert _upsert_market(richer, 54.32, 10.13, False, "Source B") == (0, 1)

    market = session.exec(select(Market).where(Market.name == "Worker enrichment market")).one()
    session.refresh(market)
    assert market.end_date == date(2031, 7, 3)
    assert (market.postal_code, market.address) == ("24103", "Rathausplatz")
    assert market.program_text == "Musik und Gaukler"
    assert market.original_text == "a much longer original text"
    assert (market.latitude, market.longitude) == (54.32, 10.13)
