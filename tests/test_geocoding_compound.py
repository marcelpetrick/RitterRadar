# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for geocoding compound place names ("Mechernich-Satzvey", "… OT …")."""

import pytest

import ritterradar.geocoding.nominatim as nominatim
from ritterradar.geocoding.nominatim import GeoResult, _city_parts

UA = "RitterRadar/test"


@pytest.mark.parametrize(
    ("city", "parts"),
    [
        ("Mechernich-Satzvey", ["Satzvey", "Mechernich"]),
        ("Schwendi - Orsenhausen", ["Orsenhausen", "Schwendi"]),
        ("Bornhagen OT Rimbach", ["Rimbach", "Bornhagen"]),
        ("Spelle / Venhaus", ["Venhaus", "Spelle"]),
        ("Elbingerode (Harz)", []),
        ("Kiel", []),
        ("St-Ulm", []),
    ],
)
def test_city_parts(city, parts):
    assert _city_parts(city) == parts


def _no_cache(monkeypatch) -> None:
    monkeypatch.setattr(nominatim, "_cache_get", lambda key: None)
    monkeypatch.setattr(nominatim, "_cache_set", lambda key, result: None)


async def test_compound_name_resolves_via_district(monkeypatch):
    _no_cache(monkeypatch)
    centroid = GeoResult(50.59, 6.65, "53894, Mechernich, Kreis Euskirchen, Deutschland", True)
    satzvey = GeoResult(50.64, 6.72, "Satzvey, Mechernich, Kreis Euskirchen, Deutschland", False)
    calls: list[object] = []

    async def fake_lookup(query: object, user_agent: str, **kwargs: object) -> GeoResult | None:
        calls.append(query)
        if query == {"postalcode": "53894", "city": "Mechernich-Satzvey"}:
            return centroid
        if query == {"postalcode": "53894", "city": "Satzvey"}:
            return satzvey
        return None

    monkeypatch.setattr(nominatim, "_nominatim_lookup", fake_lookup)
    result = await nominatim.geocode(
        "53894, Mechernich-Satzvey",
        UA,
        country_code="DE",
        postal_code="53894",
        city="Mechernich-Satzvey",
    )
    assert result == satzvey
    assert calls == [
        {"postalcode": "53894", "city": "Mechernich-Satzvey"},
        {"postalcode": "53894", "city": "Satzvey"},
    ]


async def test_compound_name_keeps_first_result_when_parts_fail(monkeypatch):
    _no_cache(monkeypatch)
    centroid = GeoResult(48.2, 9.9, "88477, Großschafhausen, Schwendi, Deutschland", True)
    calls: list[object] = []

    async def fake_lookup(query: object, user_agent: str, **kwargs: object) -> GeoResult | None:
        calls.append(query)
        return (
            centroid if query == {"postalcode": "88477", "city": "Schwendi - Orsenhausen"} else None
        )

    monkeypatch.setattr(nominatim, "_nominatim_lookup", fake_lookup)
    result = await nominatim.geocode(
        "88477, Schwendi - Orsenhausen",
        UA,
        country_code="DE",
        postal_code="88477",
        city="Schwendi - Orsenhausen",
    )
    assert result == centroid
    assert len(calls) == 3


async def test_known_hyphenated_town_needs_no_part_lookups(monkeypatch):
    _no_cache(monkeypatch)
    town = GeoResult(51.57, 7.31, "Castrop-Rauxel, Kreis Recklinghausen, Deutschland", False)
    calls: list[object] = []

    async def fake_lookup(query: object, user_agent: str, **kwargs: object) -> GeoResult:
        calls.append(query)
        return town

    monkeypatch.setattr(nominatim, "_nominatim_lookup", fake_lookup)
    result = await nominatim.geocode(
        "44575, Castrop-Rauxel", UA, country_code="DE", postal_code="44575", city="Castrop-Rauxel"
    )
    assert result == town
    assert len(calls) == 1
