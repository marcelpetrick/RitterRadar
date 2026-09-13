# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for city-aware geocode validation, certainty and cache promotion."""

from dataclasses import replace
from typing import Any

import pytest

import ritterradar.geocoding.nominatim as nominatim
from ritterradar.geocoding.nominatim import GeoResult, _blocking_lookup, _cache_key, _city_matches

UA = "RitterRadar/test"


@pytest.mark.parametrize(
    ("display_name", "city", "expected"),
    [
        ("86732, Oettingen i.Bay., Landkreis Donau-Ries, Bayern", "Oettingen", True),
        ("Elbingerode, Oberharz am Brocken, Landkreis Harz", "Elbingerode (Harz)", True),
        ("38889, Hüttenrode, Blankenburg, Landkreis Harz", "Elbingerode (Harz)", False),
        ("48480, Spelle, Samtgemeinde Spelle, Landkreis Emsland", "Spelle / Venhaus", True),
        ("76149, Neureut, Karlsruhe, Baden-Württemberg", "Karlsruhe-Neureut", True),
        ("72351, Erlaheim, Geislingen, Zollernalbkreis", "Geislingen an der Steige", False),
        ("Au, Bezirk Bregenz, Vorarlberg", "Au", False),
    ],
)
def test_city_matches(display_name, city, expected):
    assert _city_matches(display_name, city) is expected


def _install_location(monkeypatch, *, display: str, raw: dict[str, Any], importance: float) -> None:
    class Location:
        latitude = 49.75
        longitude = 8.12
        address = display

    Location.importance = importance  # type: ignore[attr-defined]
    Location.raw = raw  # type: ignore[attr-defined]

    class FakeNominatim:
        def __init__(self, *, user_agent: str) -> None:
            pass

        def geocode(self, query: object, **kwargs: Any) -> object:
            return Location()

    monkeypatch.setattr("geopy.geocoders.Nominatim", FakeNominatim)


def test_town_boundary_without_postcode_is_accepted_and_certain(monkeypatch):
    _install_location(
        monkeypatch,
        display="Elbingerode, Oberharz am Brocken, Landkreis Harz, Sachsen-Anhalt, Deutschland",
        raw={"type": "administrative", "addresstype": "town", "address": {"country_code": "de"}},
        importance=0.39,
    )
    result = _blocking_lookup(
        {"postalcode": "38875", "city": "Elbingerode (Harz)"},
        UA,
        country_code="DE",
        postal_code="38875",
        city="Elbingerode (Harz)",
    )
    assert result is not None
    assert result.uncertain is False


def test_boundary_naming_another_town_is_rejected(monkeypatch):
    _install_location(
        monkeypatch,
        display="Hüttenrode, Blankenburg, Landkreis Harz, Sachsen-Anhalt, Deutschland",
        raw={"type": "administrative", "addresstype": "village", "address": {"country_code": "de"}},
        importance=0.2,
    )
    result = _blocking_lookup(
        {"postalcode": "38889", "city": "Elbingerode (Harz)"},
        UA,
        country_code="DE",
        postal_code="38889",
        city="Elbingerode (Harz)",
    )
    assert result is None


def test_postcode_centroid_in_another_village_stays_uncertain(monkeypatch):
    _install_location(
        monkeypatch,
        display="55599, Siefersheim, Wöllstein, Landkreis Alzey-Worms, Deutschland",
        raw={"type": "postcode", "address": {"country_code": "de", "postcode": "55599"}},
        importance=0.12,
    )
    result = _blocking_lookup(
        {"postalcode": "55599"}, UA, country_code="DE", postal_code="55599", city="Eckelsheim"
    )
    assert result is not None
    assert result.uncertain is True


def test_county_result_stays_uncertain_even_when_named_like_the_city(monkeypatch):
    _install_location(
        monkeypatch,
        display="Landkreis Harz, Sachsen-Anhalt, Deutschland",
        raw={"type": "administrative", "addresstype": "county", "address": {"country_code": "de"}},
        importance=0.6,
    )
    result = _blocking_lookup("Harz", UA, country_code="DE", city="Harz")
    assert result is not None
    assert result.uncertain is True


def _previous_key(city: str, postal_code: str) -> str:
    return _cache_key(
        f"{postal_code}, {city}", "DE", postal_code, city, nominatim._PREVIOUS_CACHE_VERSION
    )


def _stub_cache(monkeypatch, entries: dict[str, GeoResult]) -> list[tuple[str, GeoResult]]:
    writes: list[tuple[str, GeoResult]] = []
    monkeypatch.setattr(nominatim, "_cache_get", entries.get)
    monkeypatch.setattr(nominatim, "_cache_set", lambda key, result: writes.append((key, result)))
    return writes


async def test_previous_entry_naming_the_city_is_promoted_without_lookup(monkeypatch):
    previous = GeoResult(48.95, 10.6, "86732, Oettingen i.Bay., Bayern, Deutschland", True)
    writes = _stub_cache(monkeypatch, {_previous_key("Oettingen", "86732"): previous})

    async def unexpected_lookup(*args: object, **kwargs: object) -> None:
        raise AssertionError("a validated previous result must not trigger a lookup")

    monkeypatch.setattr(nominatim, "_nominatim_lookup", unexpected_lookup)
    result = await nominatim.geocode(
        "86732, Oettingen", UA, country_code="DE", postal_code="86732", city="Oettingen"
    )
    assert result == replace(previous, uncertain=False)
    assert writes[0][0].startswith("market-v3|de|86732|")


async def test_certain_previous_entry_is_reused_as_is(monkeypatch):
    previous = GeoResult(50.1, 8.7, "60311, Innenstadt, Frankfurt am Main, Deutschland", False)
    writes = _stub_cache(monkeypatch, {_previous_key("Bornheim", "60311"): previous})

    async def unexpected_lookup(*args: object, **kwargs: object) -> None:
        raise AssertionError("certain results must not trigger a lookup")

    monkeypatch.setattr(nominatim, "_nominatim_lookup", unexpected_lookup)
    result = await nominatim.geocode(
        "60311, Bornheim", UA, country_code="DE", postal_code="60311", city="Bornheim"
    )
    assert result == previous
    assert writes == [(_cache_key("60311, Bornheim", "DE", "60311", "Bornheim"), previous)]


async def test_uncertain_previous_entry_for_another_place_is_refreshed(monkeypatch):
    previous = GeoResult(51.77, 10.87, "38889, Hüttenrode, Blankenburg, Deutschland", True)
    writes = _stub_cache(monkeypatch, {_previous_key("Elbingerode (Harz)", "38889"): previous})
    town = GeoResult(51.77, 10.8, "Elbingerode, Oberharz am Brocken, Deutschland", False)
    calls: list[dict[str, object]] = []

    async def fake_lookup(query: object, user_agent: str, **kwargs: object) -> GeoResult:
        calls.append(kwargs)
        return town

    monkeypatch.setattr(nominatim, "_nominatim_lookup", fake_lookup)
    result = await nominatim.geocode(
        "38889, Elbingerode (Harz)",
        UA,
        country_code="DE",
        postal_code="38889",
        city="Elbingerode (Harz)",
    )
    assert result == town
    assert calls[0]["city"] == "Elbingerode (Harz)"
    assert writes[-1][1] == town


async def test_previous_coordinates_are_kept_when_refresh_finds_nothing(monkeypatch):
    previous = GeoResult(50.4, 10.5, "98631, Queienfeld, Grabfeld, Deutschland", True)
    writes = _stub_cache(monkeypatch, {_previous_key("Römhild", "98631"): previous})

    async def nothing_found(query: object, user_agent: str, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(nominatim, "_nominatim_lookup", nothing_found)
    result = await nominatim.geocode(
        "98631, Römhild", UA, country_code="DE", postal_code="98631", city="Römhild"
    )
    assert result == previous
    assert writes == [(_cache_key("98631, Römhild", "DE", "98631", "Römhild"), previous)]
