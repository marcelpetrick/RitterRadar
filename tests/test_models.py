# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for SQLModel table models."""

from datetime import date, datetime, timezone

import pytest
from sqlmodel import Session, select

from ritterradar.models.crawl_job import CrawlJob
from ritterradar.models.market import Market
from ritterradar.models.source import Source
from ritterradar.models.user_settings import UserSettings


def test_market_defaults(session: Session):
    m = Market(
        name="Testmarkt",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 3),
        source_url="https://example.com/markt",
        source_name="Test",
        original_text="original",
    )
    session.add(m)
    session.flush()
    assert m.id is not None
    assert m.market_type == "medieval"
    assert m.hidden is False
    assert m.country == "DE"
    assert m.confidence_score == 1.0
    assert m.geocode_uncertain is False


def test_market_unique_constraint(session: Session):
    """Duplicate (name, start_date, source_url) should raise IntegrityError."""
    from sqlalchemy.exc import IntegrityError

    m1 = Market(
        name="Dup",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 2),
        source_url="https://example.com/dup",
        source_name="Test",
    )
    m2 = Market(
        name="Dup",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 3),
        source_url="https://example.com/dup",
        source_name="Test",
    )
    session.add(m1)
    session.flush()
    session.add(m2)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_source_defaults(session: Session):
    s = Source(name="MySrc", base_url="https://example.com", adapter_name="generic_table")
    session.add(s)
    session.flush()
    assert s.enabled is True
    assert s.last_crawled_at is None
    assert s.last_error is None


def test_crawl_job_defaults(session: Session):
    src = Source(name="JobSrc", base_url="https://example.com", adapter_name="generic_table")
    session.add(src)
    session.flush()

    job = CrawlJob(source_id=src.id or 1, source_name="JobSrc")
    session.add(job)
    session.flush()

    assert job.status == "pending"
    assert job.events_discovered == 0
    assert job.events_inserted == 0
    assert job.error_message is None


def test_user_settings_defaults():
    """UserSettings defaults are correct without touching the shared DB."""
    row = UserSettings()
    assert row.id == 1
    assert row.default_radius_km == 100.0
    assert row.home_latitude is None
    assert row.default_month_offset_start == 0
    assert row.default_month_offset_end == 12


def test_market_timestamps_utc(session: Session):
    m = Market(
        name="TsTest",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 1),
        source_url="https://example.com/ts",
        source_name="Test",
    )
    session.add(m)
    session.flush()
    # created_at should be a recent datetime
    assert isinstance(m.created_at, datetime)
    delta = datetime.now(timezone.utc) - m.created_at.replace(tzinfo=timezone.utc)
    assert delta.total_seconds() < 5
