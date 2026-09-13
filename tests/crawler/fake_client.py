# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Offline stand-in for PoliteHttpClient used by adapter tests."""

import json
from dataclasses import dataclass, field
from typing import Any

PageValue = str | tuple[str, int] | Exception


@dataclass
class FakeResponse:
    text: str
    status_code: int = 200

    @property
    def content(self) -> bytes:
        return self.text.encode()

    def json(self) -> Any:
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@dataclass
class FakeClient:
    """Serves canned pages by URL.

    A page value is the body text, a ``(text, status_code)`` tuple, or an
    exception to raise. Unknown URLs answer 404.
    """

    pages: dict[str, PageValue]
    requested: list[str] = field(default_factory=list)

    async def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.requested.append(url)
        value = self.pages.get(url)
        if value is None:
            return FakeResponse("", 404)
        if isinstance(value, Exception):
            raise value
        if isinstance(value, tuple):
            return FakeResponse(*value)
        return FakeResponse(value)
