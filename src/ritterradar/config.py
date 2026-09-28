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

from pydantic import Field, SecretStr, field_validator
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
    workers: int = Field(default=3, ge=0, le=8)
    geocoder_email: str = "ritterradar@localhost"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    crawl_interval_hours: float = Field(default=24, ge=0.01, le=8760)
    allowed_hosts: list[str] = ["127.0.0.1", "localhost", "::1"]
    auth_token: SecretStr | None = None
    offline: bool = False
    request_limit: int = Field(default=120, ge=10, le=10000)
    request_concurrency: int = Field(default=16, ge=1, le=64)
    max_response_bytes: int = Field(default=8_000_000, ge=1024, le=32_000_000)
    max_crawl_records: int = Field(default=10000, ge=1, le=50000)
    crawl_timeout_seconds: float = Field(default=900, ge=1, le=3600)
    max_crawl_pages: int = Field(default=50, ge=1, le=100)
    queue_limit: int = Field(default=32, ge=1, le=256)
    cache_days: int = Field(default=30, ge=1, le=365)

    @field_validator("auth_token")
    @classmethod
    def require_substantial_token(cls, token: SecretStr | None) -> SecretStr | None:
        if token is not None and len(token.get_secret_value()) < 32:
            raise ValueError("RITTERRADAR_AUTH_TOKEN must contain at least 32 characters")
        return token


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()
