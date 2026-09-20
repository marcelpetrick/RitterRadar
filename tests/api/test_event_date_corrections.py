# SPDX-License-Identifier: GPL-3.0-or-later
"""Date corrections in iCal must not leave duplicate active listings."""

from dataclasses import replace
from datetime import UTC, date, datetime

from sqlmodel import select

from ritterradar.crawler.base_adapter import MarketData
from ritterradar.crawler.worker import _upsert_market
from ritterradar.models.market import Market
from tests.api.test_markets import _make_market

URL = "https://www.taterman.at/termin/regression-date-correction/"


def test_ical_date_correction_updates_one_record(session):
    event = MarketData(
        name="Mittelalter Spektakel",
        start_date=date(2037, 9, 26),
        end_date=date(2037, 9, 27),
        city="Judenburg",
        postal_code="8750",
        country="AT",
        source_url=URL,
    )
    assert _upsert_market(event, 47.14, 14.63, False, "Taterman.at") == (1, 0)
    corrected = replace(event, start_date=date(2037, 9, 25))
    assert _upsert_market(corrected, 47.14, 14.63, False, "Taterman.at") == (0, 1)
    rows = session.exec(select(Market).where(Market.source_url == URL)).all()
    assert len(rows) == 1
    assert rows[0].start_date == date(2037, 9, 25)


def test_old_duplicate_dates_are_suppressed_but_recurring_dates_remain(client, session):
    for start, end, updated in [(26, 27, 1), (25, 27, 2), (18, 20, 1)]:
        _make_market(
            session,
            name="Judenburg correction",
            source_name="Taterman.at",
            source_url=URL,
            start_date=date(2038, 9, start),
            end_date=date(2038, 9, end),
            updated_at=datetime(2038, 9, updated, tzinfo=UTC),
        )
    rows = client.get("/api/markets?date_from=2038-09-01&date_to=2038-09-30").json()
    assert [row["start_date"] for row in rows] == ["2038-09-18", "2038-09-25"]


def test_corrected_event_outside_month_does_not_reveal_old_dates(client, session):
    for start, end, updated in [
        (date(2039, 8, 30), date(2039, 9, 2), 1),
        (date(2039, 8, 29), date(2039, 8, 31), 2),
    ]:
        _make_market(
            session,
            name="Moved into August",
            source_name="Taterman.at",
            source_url=URL,
            start_date=start,
            end_date=end,
            updated_at=datetime(2039, 8, updated, tzinfo=UTC),
        )
    rows = client.get("/api/markets?date_from=2039-09-01&date_to=2039-09-30").json()
    assert rows == []
