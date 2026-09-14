# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for constrained Nominatim market geocoding."""

from typing import Any

import ritterradar.geocoding.nominatim as nominatim
from ritterradar.geocoding.nominatim import (
    GeoResult,
    _blocking_lookup,
    _cache_key,
    _legacy_result_matches,
)


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
    assert constrained.startswith("market-v4|de|55444|")
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


def test_legacy_cache_match_requires_expected_postal_code_and_country():
    valid = GeoResult(49.94, 7.73, "55444, Dörrebach, Deutschland", True)
    wrong_city = GeoResult(52.48, 13.35, "Schöneberg, Berlin, Deutschland", True)

    assert _legacy_result_matches(valid, "DE", "55444") is True
    assert _legacy_result_matches(wrong_city, "DE", "55444") is False
    assert _legacy_result_matches(valid, "AT", "55444") is False


async def test_market_geocode_promotes_matching_legacy_cache_entry(monkeypatch):
    legacy = GeoResult(49.94, 7.73, "55444, Schöneberg, Landkreis Bad Kreuznach, Deutschland", True)
    cache_entries = {"55444, schöneberg": legacy}
    writes = []

    monkeypatch.setattr(nominatim, "_cache_get", cache_entries.get)
    monkeypatch.setattr(nominatim, "_cache_set", lambda key, result: writes.append((key, result)))

    async def unexpected_lookup(*args, **kwargs):
        raise AssertionError("validated legacy result should avoid a network lookup")

    monkeypatch.setattr(nominatim, "_nominatim_lookup", unexpected_lookup)

    result = await nominatim.geocode(
        "55444, Schöneberg",
        "RitterRadar/test",
        country_code="DE",
        postal_code="55444",
        city="Schöneberg",
    )

    # The entry names the requested town, so it is promoted as a certain result.
    assert result == GeoResult(49.94, 7.73, legacy.display_name, False)
    assert writes[0][0].startswith("market-v4|de|55444|")
    assert writes[0][1] == result
