# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for the Haversine distance formula."""

import pytest

from ritterradar.geocoding.haversine import distance_km

# Known distances (approximate, within ±2 km)
CASES = [
    # Berlin → Munich ≈ 504 km
    (52.5200, 13.4050, 48.1351, 11.5820, 504, 10),
    # Same point → 0
    (48.0, 11.0, 48.0, 11.0, 0, 0.001),
    # Cologne → Frankfurt ≈ 152 km (straight-line)
    (50.9333, 6.9600, 50.1109, 8.6821, 152, 10),
    # Hamburg → Dresden ≈ 378 km (straight-line)
    (53.5753, 10.0153, 51.0504, 13.7373, 378, 10),
]


@pytest.mark.parametrize("lat1,lon1,lat2,lon2,expected,tol", CASES)
def test_distance_km_known_pairs(lat1, lon1, lat2, lon2, expected, tol):
    result = distance_km(lat1, lon1, lat2, lon2)
    assert abs(result - expected) <= tol, f"Expected ~{expected} km, got {result:.1f} km"


def test_distance_non_negative():
    assert distance_km(0, 0, 0, 0) >= 0
    assert distance_km(52.0, 13.0, 48.0, 11.0) > 0


def test_distance_symmetric():
    a = distance_km(52.0, 13.0, 48.0, 11.0)
    b = distance_km(48.0, 11.0, 52.0, 13.0)
    assert abs(a - b) < 0.001
