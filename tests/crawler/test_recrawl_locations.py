# SPDX-License-Identifier: GPL-3.0-or-later
"""A parser correction must repair persisted data and invalidate old coordinates."""

from dataclasses import replace
from datetime import date

import pytest
from sqlmodel import select

from ritterradar.crawler.base_adapter import MarketData
from ritterradar.crawler.worker import _get_trusted_coordinates, _upsert_market
from ritterradar.models.market import Market
from tests.crawler.test_worker_process import _make_job, _StubAdapter, _worker


def _event(suffix):
    return MarketData(
        name="Elfia regression " + suffix,
        start_date=date(2036, 9, 19),
        end_date=date(2036, 9, 20),
        country="NL",
        city="BE Arcen",
        postal_code="5944",
        source_url="https://example.com/elfia/" + suffix,
    )


@pytest.mark.parametrize("resolved", [True, False])
def test_corrected_location_replaces_old_fields_and_coordinates(session, resolved):
    original = _event(str(resolved))
    _upsert_market(original, 51.0, 6.0, False, "Trollfelsen.de")
    corrected = replace(original, city="Arcen", postal_code="5944 BE", market_type="fantasy")
    assert _get_trusted_coordinates(corrected) is None
    coords = (51.47, 6.18) if resolved else (None, None)
    assert _upsert_market(corrected, *coords, False, "Trollfelsen.de") == (0, 1)
    row = session.exec(select(Market).where(Market.source_url == original.source_url)).one()
    assert (row.city, row.postal_code, row.market_type) == ("Arcen", "5944 BE", "fantasy")
    assert (row.latitude, row.longitude) == coords


def test_same_postcode_in_different_countries_does_not_merge(session):
    original = _event("countries")
    _upsert_market(original, None, None, False, "A")
    foreign = replace(original, country="DE", source_url="https://other.example/event")
    assert _upsert_market(foreign, None, None, False, "B") == (1, 0)


async def test_failed_geocoding_is_reused_within_one_crawl(session, monkeypatch):
    import ritterradar.crawler.worker as worker

    first = _event("uncached")
    second = replace(first, name="Another festival", source_url="https://example.com/another")
    monkeypatch.setattr(worker, "get_adapter", lambda _: _StubAdapter([first, second]))
    calls = []

    async def missing(query, *args, **kwargs):
        calls.append(query)
        return None

    monkeypatch.setattr(worker, "geocode", missing)
    _, job_id = _make_job(session, "Repeated missing address")
    await _worker()._process(job_id, None)
    assert calls == ["5944, BE Arcen"]


async def test_worker_does_not_geocode_or_store_cancelled_or_invalid_events(session, monkeypatch):
    import ritterradar.crawler.worker as worker

    event = _event("excluded")
    entries = [
        replace(event, name="ABGESAGT Ritterfest"),
        replace(event, name="Römerfest"),
        replace(event, end_date=date(2036, 9, 1)),
    ]
    monkeypatch.setattr(worker, "get_adapter", lambda _: _StubAdapter(entries))

    async def unexpected(*args, **kwargs):
        raise AssertionError("excluded events must not consume geocoder requests")

    monkeypatch.setattr(worker, "geocode", unexpected)
    _, job_id = _make_job(session, "Out of scope regression")
    await _worker()._process(job_id, None)
    assert not session.exec(select(Market).where(Market.source_url == event.source_url)).all()
