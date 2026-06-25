# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
"""Application-wide configuration via pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_prefix="RITTERRADAR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    sources_file: Path = Path("config/sources.yaml")
    db_path: Path = Path("data/ritterradar.db")
    workers: int = 3
    geocoder_email: str = "ritterradar@localhost"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    crawl_interval_hours: int = 24


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()
