# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Offline stand-in for PoliteHttpClient used by adapter tests."""

from dataclasses import dataclass, field


@dataclass
class FakeResponse:
    text: str
    status_code: int = 200

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@dataclass
class FakeClient:
    """Serves canned pages by URL; unknown URLs answer 404."""

    pages: dict[str, str]
    requested: list[str] = field(default_factory=list)

    async def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.requested.append(url)
        if url not in self.pages:
            return FakeResponse("", 404)
        return FakeResponse(self.pages[url])
