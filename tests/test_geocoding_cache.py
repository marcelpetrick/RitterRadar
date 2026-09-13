# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for the geocoder cache, rate-limited lookup and result validation."""

import asyncio
from typing import Any

import ritterradar.geocoding.nominatim as nominatim
from ritterradar.geocoding.nominatim import GeoResult, _blocking_lookup, _matches_expected_location


def _install_fake_nominatim(monkeypatch, location: object) -> None:
    class FakeNominatim:
        def __init__(self, *, user_agent: str) -> None:
            self.user_agent = user_agent

        def geocode(self, query: object, **kwargs: Any) -> object:
            return location

    monkeypatch.setattr("geopy.geocoders.Nominatim", FakeNominatim)


async def test_geocode_blank_query_returns_none():
    assert await nominatim.geocode("   ", "RitterRadar/test") is None


def test_cache_roundtrip_inserts_and_updates():
    key = "cache roundtrip test"
    assert nominatim._cache_get(key) is None
    nominatim._cache_set(key, GeoResult(1.0, 2.0, "first", False))
    nominatim._cache_set(key, GeoResult(3.0, 4.0, "second", True))
    assert nominatim._cache_get(key) == GeoResult(3.0, 4.0, "second", True)


async def test_geocode_returns_cached_free_form_result_without_lookup(monkeypatch):
    cached = GeoResult(50.0, 8.0, "Cached Town, Deutschland", False)
    nominatim._cache_set("cached free form town", cached)

    async def unexpected_lookup(*args: object, **kwargs: object) -> None:
        raise AssertionError("cached result must not trigger a lookup")

    monkeypatch.setattr(nominatim, "_nominatim_lookup", unexpected_lookup)
    assert await nominatim.geocode("  Cached Free Form Town ", "RitterRadar/test") == cached


async def test_geocode_caches_successful_constrained_lookup(monkeypatch):
    found = GeoResult(54.32, 10.13, "24103 Kiel, Deutschland", False)

    async def fake_lookup(query: object, user_agent: str, **kwargs: object) -> GeoResult:
        return found

    monkeypatch.setattr(nominatim, "_nominatim_lookup", fake_lookup)
    result = await nominatim.geocode(
        "Unique cache test Kiel", "RitterRadar/test", country_code="DE", city="Kiel"
    )
    assert result == found
    key = nominatim._cache_key("Unique cache test Kiel", "DE", None, "Kiel")
    assert nominatim._cache_get(key) == found


async def test_nominatim_lookup_waits_for_rate_limit_and_returns_result(monkeypatch):
    expected = GeoResult(1.0, 2.0, "somewhere", False)
    monkeypatch.setattr(nominatim, "_RATE_LIMIT_SECONDS", 0.01)
    monkeypatch.setattr(nominatim, "_last_request_time", asyncio.get_running_loop().time())
    monkeypatch.setattr(nominatim, "_blocking_lookup", lambda query, ua, **kw: expected)
    assert await nominatim._nominatim_lookup("somewhere", "RitterRadar/test") == expected


async def test_nominatim_lookup_swallows_geocoder_errors(monkeypatch):
    def failing_lookup(query: object, ua: str, **kwargs: object) -> None:
        raise RuntimeError("service unavailable")

    monkeypatch.setattr(nominatim, "_RATE_LIMIT_SECONDS", 0.0)
    monkeypatch.setattr(nominatim, "_blocking_lookup", failing_lookup)
    assert await nominatim._nominatim_lookup("somewhere", "RitterRadar/test") is None


def test_blocking_lookup_returns_none_when_nothing_is_found(monkeypatch):
    _install_fake_nominatim(monkeypatch, None)
    assert _blocking_lookup("Nirgendwo", "RitterRadar/test") is None


def test_blocking_lookup_marks_coarse_results_uncertain(monkeypatch):
    class CountryLocation:
        latitude = 51.0
        longitude = 10.0
        address = "Deutschland"
        importance = 0.9
        raw: dict[str, Any] = {"type": "country"}

    _install_fake_nominatim(monkeypatch, CountryLocation())
    result = _blocking_lookup("Deutschland", "RitterRadar/test")
    assert result == GeoResult(51.0, 10.0, "Deutschland", True)


def test_constrained_match_requires_address_details():
    assert _matches_expected_location({}, None, None) is True
    assert _matches_expected_location({}, "DE", None) is False
