# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression coverage for calendar-month results and scope."""

from datetime import date

import pytest

from tests.api.test_markets import _make_market


def test_calendar_month_includes_events_overlapping_either_boundary(client, session):
    spans = {
        "Starts August": (date(2034, 8, 30), date(2034, 9, 2)),
        "Ends October": (date(2034, 9, 29), date(2034, 10, 2)),
        "Spans month": (date(2034, 8, 1), date(2034, 10, 31)),
        "Last day": (date(2034, 9, 30), date(2034, 9, 30)),
        "Past": (date(2034, 8, 1), date(2034, 8, 31)),
        "Future": (date(2034, 10, 1), date(2034, 10, 2)),
        "Broken": (date(2034, 9, 20), date(2034, 9, 10)),
    }
    for name, (start, end) in spans.items():
        _make_market(session, name=name, start_date=start, end_date=end)
    response = client.get("/api/markets?date_from=2034-09-01&date_to=2034-09-30")
    assert response.status_code == 200
    assert {r["name"] for r in response.json()} == {
        "Starts August",
        "Ends October",
        "Spans month",
        "Last day",
    }


def test_previously_stored_cancelled_and_unrelated_rows_are_filtered(client, session):
    for name in ["ABGESAGT Rittermarkt", "Mähen mit der Sense", "Wikingerfest September"]:
        _make_market(
            session,
            name=name,
            start_date=date(2035, 9, 19),
            end_date=date(2035, 9, 20),
            source_name="Fyndling.de",
        )
    response = client.get("/api/markets?date_from=2035-09-01&date_to=2035-09-30")
    assert [r["name"] for r in response.json()] == ["Wikingerfest September"]


@pytest.mark.parametrize(
    "query",
    [
        "date_from=2026-10-01&date_to=2026-09-01",
        "lat=91&lon=0",
        "lat=0&lon=181",
        "lat=0&lon=0&radius_km=-1",
    ],
)
def test_invalid_filter_bounds_are_rejected(client, query):
    assert client.get(f"/api/markets?{query}").status_code == 422
