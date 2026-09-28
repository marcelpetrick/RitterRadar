# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Settings API — user profile (home location, filter defaults)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlmodel import Session, delete

from ritterradar.config import get_settings
from ritterradar.database.session import get_session
from ritterradar.geocoding.nominatim import geocode
from ritterradar.models.geocoding_cache import GeocodingCache
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
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    home_latitude: float | None = Field(default=None, ge=-90, le=90)
    home_longitude: float | None = Field(default=None, ge=-180, le=180)
    home_label: str | None = Field(default=None, max_length=500)
    default_radius_km: float | None = Field(default=None, ge=0, le=1024)
    default_month_offset_start: int | None = Field(default=None, ge=0, le=12)
    default_month_offset_end: int | None = Field(default=None, ge=0, le=12)

    @model_validator(mode="after")
    def validate_pair(self) -> "SettingsIn":
        if {"home_latitude", "home_longitude"} <= self.model_fields_set and (
            (self.home_latitude is None) != (self.home_longitude is None)
        ):
            raise ValueError("Provide both home coordinates or clear both")
        start, end = self.default_month_offset_start, self.default_month_offset_end
        if start is not None and end is not None and start > end:
            raise ValueError("Month offsets must be ordered")
        return self


class GeocodeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: str = Field(min_length=1, max_length=300)


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
    values = {key: getattr(row, key) for key in SettingsIn.model_fields}
    updates = body.model_dump(exclude_unset=True)
    if any(value is None and key.startswith("default_") for key, value in updates.items()):
        raise HTTPException(422, "Default settings cannot be null")
    values.update(updates)
    try:
        validated = SettingsIn.model_validate(values)
    except ValidationError:
        raise HTTPException(422, "Invalid combined settings") from None
    for key, value in validated.model_dump().items():
        setattr(row, key, value)
    session.add(row)
    return SettingsOut(
        home_latitude=row.home_latitude,
        home_longitude=row.home_longitude,
        home_label=row.home_label,
        default_radius_km=row.default_radius_km,
        default_month_offset_start=row.default_month_offset_start,
        default_month_offset_end=row.default_month_offset_end,
    )


@router.post("/geocode")
async def geocode_query(
    body: GeocodeIn,
) -> dict[str, object]:
    """Geocode an address and return coordinates."""
    q = body.q.strip()
    app_settings = get_settings()
    if app_settings.offline:
        raise HTTPException(503, "Geocoding is disabled in offline mode")
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


@router.delete("/history")
def clear_private_settings(session: Annotated[Session, Depends(get_session)]) -> dict[str, bool]:
    """Clear saved home and all geocoding history; retain event records."""
    row = _get_or_create(session)
    row.home_latitude = row.home_longitude = None
    row.home_label = None
    session.add(row)
    session.exec(delete(GeocodingCache))
    return {"cleared": True}
