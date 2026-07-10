# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for constrained Nominatim market geocoding."""

from typing import Any

import ritterradar.geocoding.nominatim as nominatim
from ritterradar.geocoding.nominatim import GeoResult, _blocking_lookup, _cache_key


class _FakeLocation:
    latitude = 49.88
    longitude = 7.75
    address = "55444 Schöneberg, Deutschland"
    importance = 0.5

    def __init__(self, address: dict[str, str]) -> None:
        self.raw: dict[str, Any] = {"type": "village", "address": address}


def _install_fake_nominatim(monkeypatch, address: dict[str, str], calls: list[dict]) -> None:
    class FakeNominatim:
        def __init__(self, *, user_agent: str) -> None:
            assert user_agent == "RitterRadar/test"

        def geocode(self, query, **kwargs):
            calls.append({"query": query, **kwargs})
            return _FakeLocation(address)

    monkeypatch.setattr("geopy.geocoders.Nominatim", FakeNominatim)


def test_market_lookup_uses_constraints_and_accepts_matching_address(monkeypatch):
    calls: list[dict] = []
    _install_fake_nominatim(
        monkeypatch,
        {"country_code": "de", "postcode": "55444"},
        calls,
    )

    result = _blocking_lookup(
        {"postalcode": "55444", "city": "Schöneberg"},
        "RitterRadar/test",
        country_code="DE",
        postal_code="55444",
    )

    assert result is not None
    assert calls[0]["country_codes"] == "de"
    assert calls[0]["addressdetails"] is True
    assert calls[0]["query"] == {"postalcode": "55444", "city": "Schöneberg"}


def test_market_lookup_rejects_postal_code_mismatch(monkeypatch):
    calls: list[dict] = []
    _install_fake_nominatim(
        monkeypatch,
        {"country_code": "de", "postcode": "10823"},
        calls,
    )

    result = _blocking_lookup(
        {"postalcode": "55444", "city": "Schöneberg"},
        "RitterRadar/test",
        country_code="DE",
        postal_code="55444",
    )

    assert result is None


def test_market_lookup_rejects_country_mismatch(monkeypatch):
    calls: list[dict] = []
    _install_fake_nominatim(
        monkeypatch,
        {"country_code": "at", "postcode": "55444"},
        calls,
    )

    result = _blocking_lookup(
        {"postalcode": "55444"},
        "RitterRadar/test",
        country_code="DE",
        postal_code="55444",
    )

    assert result is None


def test_market_cache_key_does_not_reuse_legacy_free_form_result():
    legacy = _cache_key("55444, Schöneberg", None, None, None)
    constrained = _cache_key("55444, Schöneberg", "DE", "55444", "Schöneberg")

    assert legacy == "55444, schöneberg"
    assert constrained.startswith("market-v2|de|55444|")
    assert constrained != legacy


async def test_market_geocode_falls_back_to_validated_postal_code(monkeypatch):
    calls = []
    postal_result = GeoResult(49.94, 7.73, "55444, Deutschland", True)

    async def fake_lookup(query, user_agent, **kwargs):
        calls.append(query)
        return postal_result if query == {"postalcode": "55444"} else None

    monkeypatch.setattr(nominatim, "_cache_get", lambda key: None)
    monkeypatch.setattr(nominatim, "_cache_set", lambda key, result: None)
    monkeypatch.setattr(nominatim, "_nominatim_lookup", fake_lookup)

    result = await nominatim.geocode(
        "55444, Schöneberg",
        "RitterRadar/test",
        country_code="DE",
        postal_code="55444",
        city="Schöneberg",
    )

    assert result == postal_result
    assert calls == [
        {"postalcode": "55444", "city": "Schöneberg"},
        {"postalcode": "55444"},
    ]
