# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Haversine great-circle distance formula — no external dependencies."""

import math


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the straight-line distance in kilometres between two WGS-84 coordinates.

    Uses the Haversine formula.  Accurate to within ~0.5 % for distances up to
    a few thousand kilometres, which is more than sufficient for European market
    discovery.

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.

    Returns:
        Distance in kilometres (always non-negative).
    """
    R = 6_371.0  # mean Earth radius in km

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))
