# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Settings API — user profile (home location, filter defaults)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from ritterradar.config import get_settings
from ritterradar.database.session import get_session
from ritterradar.geocoding.nominatim import geocode
from ritterradar.models.user_settings import UserSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsOut(BaseModel):
    home_latitude: float | None
    home_longitude: float | None
    home_label: str | None
    default_radius_km: float
    default_month_offset_start: int
    default_month_offset_end: int


class SettingsIn(BaseModel):
    home_latitude: float | None = None
    home_longitude: float | None = None
    home_label: str | None = None
    default_radius_km: float | None = None
    default_month_offset_start: int | None = None
    default_month_offset_end: int | None = None


def _get_or_create(session: Session) -> UserSettings:
    row = session.get(UserSettings, 1)
    if row is None:
        row = UserSettings()
        session.add(row)
        session.flush()
    return row


@router.get("", response_model=SettingsOut)
async def get_user_settings(
    session: Annotated[Session, Depends(get_session)],
) -> SettingsOut:
    """Return the current user settings."""
    row = _get_or_create(session)
    return SettingsOut(
        home_latitude=row.home_latitude,
        home_longitude=row.home_longitude,
        home_label=row.home_label,
        default_radius_km=row.default_radius_km,
        default_month_offset_start=row.default_month_offset_start,
        default_month_offset_end=row.default_month_offset_end,
    )


@router.put("", response_model=SettingsOut)
async def update_user_settings(
    body: SettingsIn,
    session: Annotated[Session, Depends(get_session)],
) -> SettingsOut:
    """Update user settings (partial update — only provided fields change)."""
    row = _get_or_create(session)
    if body.home_latitude is not None:
        row.home_latitude = body.home_latitude
    if body.home_longitude is not None:
        row.home_longitude = body.home_longitude
    if body.home_label is not None:
        row.home_label = body.home_label
    if body.default_radius_km is not None:
        row.default_radius_km = body.default_radius_km
    if body.default_month_offset_start is not None:
        row.default_month_offset_start = body.default_month_offset_start
    if body.default_month_offset_end is not None:
        row.default_month_offset_end = body.default_month_offset_end
    session.add(row)
    return SettingsOut(
        home_latitude=row.home_latitude,
        home_longitude=row.home_longitude,
        home_label=row.home_label,
        default_radius_km=row.default_radius_km,
        default_month_offset_start=row.default_month_offset_start,
        default_month_offset_end=row.default_month_offset_end,
    )


@router.get("/geocode")
async def geocode_query(
    q: Annotated[str, Query(description="Address, city name, or German postal code")],
) -> dict[str, object]:
    """Geocode an address and return coordinates."""
    app_settings = get_settings()
    user_agent = f"RitterRadar/0.0 ({app_settings.geocoder_email})"
    result = await geocode(q, user_agent)
    if result is None:
        return {"found": False, "query": q}
    return {
        "found": True,
        "query": q,
        "latitude": result.latitude,
        "longitude": result.longitude,
        "display_name": result.display_name,
        "uncertain": result.uncertain,
    }
